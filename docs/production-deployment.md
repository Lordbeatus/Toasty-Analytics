# Production deployment

This guide covers running ToastyAnalytics outside local development: building the
image, running the Compose stack, deploying to Kubernetes, and deploying to
managed hosts.

## Prerequisites

- Docker 24+ with Compose v2
- PostgreSQL 15+ and Redis 7+ (or the containers from the Compose stacks)
- Python 3.10+ for local checks

## Configuration

Copy `.env.example` to `.env` on the host and set real values:

```bash
TOASTYANALYTICS_DB_URL=postgresql://user:password@db-host:5432/toastyanalytics
REDIS_URL=redis://redis-host:6379/0
CELERY_BROKER_URL=redis://redis-host:6379/0
CELERY_RESULT_BACKEND=redis://redis-host:6379/1
SENTRY_DSN=https://...@sentry.io/project

# Authentication (required unless AUTH_ENABLED=false)
JWT_SECRET_KEY=<48+ random bytes>
TOASTY_API_KEYS=prod-key:service-user:admin:*
```

Generate the JWT secret with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Notes:

- `toastyanalytics/config.py` reads these values once at import time.
- The API creates missing tables on startup. There are no Alembic migrations in
  the repository yet, so schema changes require a manual migration step.
- Never commit `.env`; it is gitignored.

## Container image

```bash
docker build -f deployment/docker/Dockerfile -t toastyanalytics:latest .
docker run --rm -p 8000:8000 --env-file .env toastyanalytics:latest
```

The image installs the package from `pyproject.toml`, runs as an unprivileged
user, and includes a health check against `/health`.

## Docker Compose

```bash
cd deployment/docker
docker compose up --build -d
docker compose ps
docker compose logs -f api
```

The default stack runs PostgreSQL, Redis, the API, a Celery worker, and Celery
beat. For per-service databases use `docker-compose.split-db.yml`; for the
gateway plus three services use `docker-compose.microservices.yml`.

Before exposing the stack publicly:

1. Replace the sample database password in the Compose file and `.env`.
2. Replace the development `JWT_SECRET_KEY` and `TOASTY_API_KEYS` from
   `.env.example`; the Compose stack forwards them from `.env`.
3. Terminate TLS at a reverse proxy or load balancer in front of port 8000.
4. Keep PostgreSQL and Redis on a private network.
5. Raise or lower `RATE_LIMIT` for expected traffic; set `RATE_LIMIT_ADMIN=0`
   only for trusted operators.

## Kubernetes

Manifests live in `deployment/kubernetes/`.

```bash
kubectl create namespace toastyanalytics

kubectl -n toastyanalytics create secret generic toastyanalytics-secrets \
  --from-literal=database-url="$TOASTYANALYTICS_DB_URL" \
  --from-literal=jwt-secret="$JWT_SECRET_KEY"

export IMAGE_TAG=<commit-sha>
envsubst < deployment/kubernetes/deployments.yaml | kubectl apply -f -

kubectl -n toastyanalytics get pods
kubectl -n toastyanalytics port-forward svc/grading-service 8000:8000
```

The manifests expect images at
`ghcr.io/lordbeatus/toasty-analytics/<service>:<tag>`; the
`.github/workflows/build.yml` workflow publishes them on tags and on `main`.
`deployment/kubernetes/istio-config.yaml` adds routing, retries, and circuit
breaking when Istio is installed.

The `deploy` workflow (`.github/workflows/deploy.yml`) automates these steps when
`KUBECONFIG`, `K8S_CONTEXT`, `DATABASE_URL`, and `JWT_SECRET_KEY` secrets are
configured. It deploys on `main`, on `v*` tags, and on manual dispatch.

## Managed hosts

### Render

`render.yaml` defines a Docker web service, a PostgreSQL database, and Redis.
Point Render at the repository and set `JWT_SECRET_KEY`, `TOASTY_API_KEYS`, and
(optionally) `SENTRY_DSN` in the dashboard; the database and Redis variables are
wired from the managed services.

### AWS ECS

`scripts/deploy-aws.sh` builds the image, pushes it to ECR, and creates or
updates the ECS service and task definition. Review the script's cluster, region,
and networking defaults before running it against a real account:

```bash
AWS_REGION=us-east-1 ./scripts/deploy-aws.sh
```

### Any container platform

Run `uvicorn toastyanalytics.api:app --host 0.0.0.0 --port 8000` from the image
with the environment variables above. Add workers with
`celery -A toastyanalytics.celery_app worker` and
`celery -A toastyanalytics.celery_app beat` when background jobs and scheduled
strategy updates are needed.

## Operations

- **Health checks:** `/health` reports API, database, and WebSocket status.
- **Logs:** the app logs to stdout; collect with the platform's log driver.
- **Error tracking:** install the `sentry` extra and set `SENTRY_DSN`.
- **Backups:** back up PostgreSQL on the usual schedule; SQLite deployments
  should use a persistent volume and file-level backups.
- **Scaling:** the API is stateless; scale replicas behind a load balancer that
  supports WebSocket upgrades. Celery workers scale independently.
- **Security:** the default app has no authentication. Put it behind an
  authenticating proxy, or wire `toastyanalytics/auth/jwt_auth.py` into the
  FastAPI app before exposing it publicly.
