# ToastyAnalytics

ToastyAnalytics grades source code across several quality dimensions and adjusts
its scoring from user feedback. It ships as a FastAPI service, a Python library,
and a CLI, with optional MCP-server and VS Code clients. It was originally built as internal tooling made for the team at Toastimer but the team realized it could be used for people beyond the team.

## What it does

- **Structural code grading.** Parses Python with `ast` to measure function and
  class layout, docstring coverage, import usage, and cyclomatic complexity, then
  scores structure, readability, best practices, and complexity.
- **Nine dimensions.** Readability reuses the code-quality analysis; accuracy
  compares an answer to a supplied reference; prompt understanding, follow-up
  quality, efficiency, and prompt quality grade generated language; speed and
  reliability score generation time and task success consistency.
- **Feedback-driven adaptation.** The meta-learning engine records feedback on
  past gradings and updates per-user scoring weights and thresholds.
- **Extensible graders.** Drop a Python grader or a YAML rule set into
  `toastyanalytics/plugins/custom/` to add your own checks.
- **HTTP API and CLI.** REST and WebSocket endpoints for integrations; a Click
  CLI for local grading and analytics.
- **Authentication and rate limits.** API keys and short-lived JWTs with scope
  checks, per-user data isolation, and per-caller, per-endpoint rate limiting
  backed by Redis with an in-memory fallback.
- **Optional neural grading.** A CodeBERT-based grader is available when PyTorch
  and Transformers are installed.

## Status

| Area | State |
| --- | --- |
| All nine dimension graders | Implemented, covered by tests |
| Meta-learning from feedback | Implemented, covered by tests |
| REST API, WebSocket events, CLI | Implemented |
| API-key and JWT auth with scopes | Implemented and enabled by default |
| Rate limiting (Redis or in-memory) | Implemented and enabled by default |
| Plugin system (Python and YAML) | Implemented |
| Neural grader | Optional, requires `[neural]` extra |
| GraphQL API | Optional module, requires Strawberry |
| Distributed tracing | Optional module; not enabled in the default app |

## Quick start

Requires Python 3.10 or newer.

```bash
git clone https://github.com/Lordbeatus/Toasty-Analytics.git
cd Toasty-Analytics

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

cp .env.example .env             # required for API authentication
uvicorn toastyanalytics.api:app --reload
```

The API is now at <http://localhost:8000>, with interactive docs at
<http://localhost:8000/docs>. `.env.example` sets a development JWT secret and
the API key `dev-local-key`; replace both before deploying.

### Authenticate

```bash
curl -X POST http://localhost:8000/auth/token \
  -H "X-API-Key: dev-local-key" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user-123"}'
```

Use the returned `access_token` as `Authorization: Bearer <token>`. Service
clients may send `X-API-Key` directly. Tokens carry only the scopes and roles
requested, and endpoints reject access to another user's data.

### Docker

```bash
cp .env.example .env
docker compose -f deployment/docker/docker-compose.yml up --build
```

That stack runs PostgreSQL, Redis, the API, a Celery worker, and Celery beat.
A split-database stack and a microservices stack live alongside it in
`deployment/docker/`.

## Usage

### Grade code over HTTP

```bash
curl -X POST http://localhost:8000/grade \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-123",
    "code": "def add(a, b):\n    return a + b\n",
    "language": "python",
    "dimensions": ["code_quality"]
  }'
```

The response contains per-dimension scores, feedback, breakdowns, and
prioritized suggestions. `POST /feedback` accepts a rating and comments for a
grading ID, which feeds the meta-learner.

### Use the library

```python
from toastyanalytics import GradingDimension, get_grader_for_dimension

grader = get_grader_for_dimension(GradingDimension.CODE_QUALITY)
result = grader.grade(code="def add(a, b):\n    return a + b\n", language="python")

print(result.score, result.feedback)
```

### Use the CLI

```bash
toastyanalytics grade examples/sample_code.py --user-id demo -d code_quality
toastyanalytics stats --user-id demo --days 7
toastyanalytics serve --port 8000
```

### Explore the endpoints

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/health` | Public | Service and database status |
| `POST` | `/auth/token` | API key | Mint a user-scoped JWT pair |
| `POST` | `/auth/refresh` | Refresh token | Mint a new access token |
| `GET` | `/auth/me` | Any credential | Caller identity, roles, scopes |
| `GET` | `/dimensions` | `grade:read` | Dimensions with an available grader |
| `POST` | `/grade` | `grade:write` | Grade a snippet |
| `POST` | `/feedback` | `grade:write` | Attach feedback to a grading |
| `GET` | `/analytics/user/{user_id}` | `analytics:read` | Submission history and trend |
| `GET` | `/strategies/{user_id}` | `analytics:read` | Learned strategies for a user |
| `WS` | `/ws/{user_id}` | JWT or API key | Live grading and learning events |

Rate limits are per caller and endpoint: `RATE_LIMIT` requests per minute,
with `X-RateLimit-*` headers on every response and `429` plus `Retry-After`
when exhausted. Callers with the `admin` role use `RATE_LIMIT_ADMIN` (0 means
unlimited). `/health`, `/`, and the docs are exempt.

## Architecture

```text
                HTTP / WebSocket
                       │
                 FastAPI app (api.py)
                       │
        ┌──────────────┼───────────────┐
        │              │               │
   Graders        Meta-learner     Database layer
 (AST, speed,   (weights and      (SQLAlchemy:
  reliability)   thresholds)       SQLite/Postgres)
        │              │               │
        └──────────────┴───────────────┘
                       │
              Celery worker and beat
```

Grading and learning both run in-process; Celery handles background work in the
Docker stacks. The `toastyanalytics/services/` modules expose the same
capabilities as standalone services for the microservice deployment.

## Project layout

```text
toastyanalytics/
├── api.py                 # FastAPI app: grading, feedback, analytics, WebSocket
├── cli/main.py            # Click CLI
├── core/                  # Base grader and shared types
├── graders/               # Nine dimension graders plus the optional neural grader
├── meta_learning/         # Feedback-driven strategy engine
├── database/              # SQLAlchemy models and database splitting helpers
├── plugins/               # Plugin loader and custom graders
├── services/              # Optional microservice entry points
├── auth/, middleware/     # JWT/API-key auth and rate limiting used by the app
├── event_sourcing/        # Event store and projections
├── messaging/             # Kafka/RabbitMQ or in-memory event broker
├── tracing/               # Optional OpenTelemetry setup
├── config.py              # Environment-backed settings
├── celery_app.py          # Celery application and scheduled tasks
tests/                     # Pytest suite
examples/                  # Runnable library and API examples
deployment/                # Docker Compose and Kubernetes manifests
mcp-server/                # MCP server (Node.js)
vscode-extension/          # VS Code client
```

## Development

```bash
pip install -e ".[dev]"

pytest                                   # unit and integration tests
black --check toastyanalytics tests
isort --check-only --profile black toastyanalytics tests
flake8 toastyanalytics tests
```

Configuration is read from environment variables; see `.env.example` and
`toastyanalytics/config.py`. `TOASTYANALYTICS_DB_URL` defaults to a local SQLite
file.

## Documentation

- [Quick start and operations](docs/quickstart.md)
- [Architecture reference](docs/architecture.md)
- [Production deployment](docs/production-deployment.md)
- [Examples](examples/README.md)

## Contributing

Issues and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for
the development workflow and [SECURITY.md](SECURITY.md) for reporting
vulnerabilities.

## License

MIT. See [LICENSE](LICENSE).
