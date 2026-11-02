# Quick start and operations

## Local development

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

cp .env.example .env
uvicorn toastyanalytics.api:app --reload
```

Endpoints:

- API and docs: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/health>

Authentication is enabled by default. `.env.example` sets a development secret
and the API key `dev-local-key`, which you can exchange for a JWT:

```bash
curl -X POST http://localhost:8000/auth/token \
  -H "X-API-Key: dev-local-key" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "demo"}'
```

Use the returned `access_token` as `Authorization: Bearer <token>`, or send
`X-API-Key` directly from a service client. Replace the development key and
secret before deploying.

By default the service stores data in `toastyanalytics.db` (SQLite). Set
`TOASTYANALYTICS_DB_URL` to use PostgreSQL:

```bash
TOASTYANALYTICS_DB_URL=postgresql://toasty:password@localhost:5432/toastyanalytics
```

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `TOASTYANALYTICS_DB_URL` | `sqlite:///toastyanalytics.db` | Database connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery broker |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/1` | Celery result backend |
| `HOST` / `PORT` | `0.0.0.0` / `8000` | Bind address |
| `AUTH_ENABLED` | `true` | Require credentials on protected routes |
| `JWT_SECRET_KEY` | unset | HS256 signing key; required when auth is enabled |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access-token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh-token lifetime |
| `TOASTY_API_KEYS` | unset | `key:user_id:roles:scopes` entries, comma separated |
| `RATE_LIMIT_ENABLED` | `true` | Enable request rate limiting |
| `RATE_LIMIT` | `60` | Requests per minute, per caller and endpoint |
| `RATE_LIMIT_ADMIN` | `0` | Admin-role limit per minute; `0` is unlimited |
| `SENTRY_DSN` | unset | Enables Sentry when set |
| `SENTRY_ENVIRONMENT` | `development` | Sentry environment tag |

Settings load from the environment and from a `.env` file in the working
directory.

## Authentication and scopes

API keys are the credential of record for services. Each entry in
`TOASTY_API_KEYS` has the form `key:user_id:roles:scopes`; roles and scopes are
separated by `|`, and `*` grants every scope.

```text
ci-key:ci-runner:grade:read|grade:write,
ops-key:operator:admin:*
```

`POST /auth/token` exchanges an API key with `token:issue` (or `*`) for a JWT
pair. Requested scopes must be a subset of the key's scopes, and requested roles
must be roles the key holds.

| Scope | Grants |
| --- | --- |
| `grade:read` | `GET /dimensions` |
| `grade:write` | `POST /grade`, `POST /feedback` |
| `analytics:read` | `GET /analytics/user/{id}`, `GET /strategies/{id}` |
| `token:issue` | Mint JWTs at `POST /auth/token` |

Non-admin callers may only access their own user ID. WebSocket clients authenticate
with `Authorization`, `?token=`, or `?api_key=`.

## Rate limiting

Requests are limited per caller and endpoint using a Redis sliding window when
`REDIS_URL` is reachable, and an in-process window otherwise. Responses include
`X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset`; exhausted
callers get `429` with `Retry-After`. `/health`, `/`, and the docs are exempt.

## Docker Compose

```bash
cp .env.example .env

cd deployment/docker
docker compose up --build -d
docker compose logs -f api
```

Services: API (8000), PostgreSQL (5432), Redis (6379), Celery worker, Celery
beat. Stop the stack with `docker compose down`.

Other stacks in the same directory:

```bash
# One database per service
docker compose -f docker-compose.split-db.yml up -d

# Independent services behind an API gateway
docker compose -f docker-compose.microservices.yml up -d
```

## CLI

```bash
toastyanalytics grade path/to/file.py --user-id demo -d code_quality
toastyanalytics grade-all ./src --user-id demo --pattern "*.py"
toastyanalytics feedback --user-id demo --session-id <grading-id> --score 4
toastyanalytics show-strategies --user-id demo
toastyanalytics stats --user-id demo --days 7
toastyanalytics serve --port 8000
```

## Tests and checks

```bash
pytest
black --check toastyanalytics tests
isort --check-only --profile black toastyanalytics tests
flake8 toastyanalytics tests
```

## Troubleshooting

**`ModuleNotFoundError: No module named 'toastyanalytics'`** — install the
package from the repository root with `pip install -e .` (or `".[dev]"`).

**Port 8000 already in use** — pass `--port 8001` to `uvicorn` or
`toastyanalytics serve`.

**PostgreSQL connection errors** — confirm the container is healthy with
`docker compose ps` and that `TOASTYANALYTICS_DB_URL` points at the `postgres`
service hostname inside Compose.

**Empty analytics** — analytics only include gradings for that user; grade a
snippet first, then query `/analytics/user/{user_id}`.

**`401 Not authenticated`** — send `X-API-Key` or a bearer token. Mint a token
with `POST /auth/token` using a configured key.

**`503 Authentication is enabled but not configured`** — set
`JWT_SECRET_KEY` and at least one entry in `TOASTY_API_KEYS`, or set
`AUTH_ENABLED=false` for a local-only run.

**`429 Too Many Requests`** — read `Retry-After`, or raise `RATE_LIMIT`.
