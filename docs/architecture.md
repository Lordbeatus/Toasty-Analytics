# Architecture

## Overview

ToastyAnalytics is a Python application with three entry points that share the
same core:

- `toastyanalytics/api.py` — FastAPI application exposing REST and WebSocket
  endpoints.
- `toastyanalytics/cli/main.py` — Click CLI for grading files and reading
  analytics.
- `toastyanalytics/services/*.py` — optional standalone services used by the
  microservice deployment.

The core (graders, meta-learner, database layer) is plain Python, so library
users call it directly without starting a server.

## Component map

```text
                       ┌─────────────────────┐
                       │      api.py         │
                       │  REST + WebSocket   │
                       └──────────┬──────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
┌───────▼────────┐      ┌─────────▼─────────┐     ┌─────────▼─────────┐
│    graders/    │      │  meta_learning/   │     │    database/      │
│ code quality   │      │ weights,          │     │ SQLAlchemy models │
│ speed          │      │ thresholds,       │     │ and sessions      │
│ reliability    │      │ strategies        │     │                   │
└───────┬────────┘      └─────────┬─────────┘     └─────────┬─────────┘
        │                         │                         │
        └──────────┬──────────────┴──────────────┬──────────┘
                   │                             │
          ┌────────▼────────┐           ┌────────▼────────┐
          │   core/types.py │           │  config.py      │
          │ shared models   │           │ env-backed      │
          └─────────────────┘           └─────────────────┘
```

## Components

### Core (`toastyanalytics/core/`)

`base_grader.py` defines `BaseGrader`, which owns weighting, threshold handling,
and the `grade()` contract. `types.py` defines `GradingDimension`, `ScoreBreakdown`,
`GraderResult`, `ImprovementSuggestion`, and the learning-strategy types shared by
every module.

### Graders (`toastyanalytics/graders/`)

| Grader | Strategy |
| --- | --- |
| `CodeQualityGraderV2` | Parses Python with `ast`; scores structure, readability, best practices, and cyclomatic complexity from real syntax data. Falls back to text heuristics for other languages. |
| `SpeedGrader` | Compares reported generation and execution time against configurable targets. |
| `ReadabilityGrader` | Reports the readability view of the code-quality analysis under its own dimension. |
| `ReliabilityGrader` | Scores success rate and score variance across recorded task attempts. |
| `AccuracyGrader` | Compares an answer to a caller-supplied reference; reports an explicit unverified score when none is given. |
| `PromptUnderstandingGrader` | Checks prompt-keyword coverage, question-type alignment, and explicit output instructions. |
| `FollowupQualityGrader` | Scores continuity with prior context, specificity, and next-step actionability. |
| `EfficiencyGrader` | Scores content density, redundancy, and length appropriateness. |
| `PromptQualityGrader` | Scores prompt specificity, clarity, and structure. |
| `NeuralGrader` | Optional CodeBERT-based scorer; falls back to heuristics when PyTorch or model weights are unavailable. |

`get_grader_for_dimension()` is the factory. `SUPPORTED_DIMENSIONS` lists the
dimensions with a concrete grader, and `/dimensions` reports exactly those.

### Meta-learning (`toastyanalytics/meta_learning/engine.py`)

`MetaLearner` reads `grading_history` rows and feedback, then writes
`learning_strategies` per user and dimension. Strategies carry adjusted weights
and thresholds. `apply_strategies_to_grader()` applies a stored strategy to a
grader instance before scoring.

### Database (`toastyanalytics/database/`)

`models.py` defines `User`, `Agent`, `GradingHistory`, `LearningStrategy`, and
`CollectiveLearning` on SQLAlchemy 2.x. `DatabaseManager` creates the engine and
creates tables on startup. SQLite is the default; set `TOASTYANALYTICS_DB_URL`
for PostgreSQL. `database_splitter.py` generates per-service database
configuration for the microservice deployment.

### API (`toastyanalytics/api.py`)

Startup creates the database manager, the meta-learner, and an asyncio event
queue. `process_events()` drains the queue and pushes events to connected
WebSocket clients. Errors are returned as `HTTPException` responses; Sentry is
initialised only when `sentry-sdk` is installed and a DSN is configured.

### Authentication and authorization (`toastyanalytics/auth/`)

`jwt_auth.py` resolves two credential types to a `TokenData` principal: API keys
from `TOASTY_API_KEYS`, and HS256 JWTs minted by `POST /auth/token` and
`POST /auth/refresh`. Tokens carry `sub`, `roles`, `scopes`, `iss`, `jti`, and
expiry. Routes depend on `require_scope("grade:write")` and similar, and
`_authorize_user()` rejects cross-user access unless the caller has the `admin`
role. WebSocket connections authenticate from a header or `?token=`/`?api_key=`.

### Rate limiting (`toastyanalytics/middleware/`)

`RateLimitMiddleware` runs before routing. It resolves a caller identity and
role tier (from the same credentials), then applies a sliding window per
identifier and endpoint with `RateLimiter`. Redis is used when reachable;
otherwise the limiter keeps in-process counters. Exceeded requests receive
`429`, `Retry-After`, and `X-RateLimit-*` headers.

### Optional modules

- `graphql_api.py` — Strawberry schema, requires the `strawberry-graphql` package.
- `tracing/` — OpenTelemetry setup, requires the tracing dependencies.
- `event_sourcing/` — append-only event store and projections.
- `messaging/` — Kafka, RabbitMQ, or in-memory event broker.

These are importable components; the default app does not enable GraphQL or
tracing.

## Request flow

### Grading

1. `RateLimitMiddleware` checks the caller's budget and sets rate-limit headers.
2. `POST /grade` authenticates the caller, checks `grade:write`, and rejects
   another user's `user_id`.
3. `POST /grade` validates the requested dimensions.
4. The database manager loads or creates the user.
5. The meta-learner supplies the user's strategies.
6. Each requested dimension is graded; strategies adjust weights and thresholds.
7. The result is written to `grading_history`.
8. A `grading_complete` event is queued for WebSocket delivery.
9. The API returns scores, feedback, suggestions, and the `grading_id`.

### Learning

1. `POST /feedback` records the rating and comments for a `grading_id`.
2. The meta-learner aggregates feedback per dimension.
3. Weights and thresholds are updated for the user.
4. `GET /strategies/{user_id}` shows the current learned strategy.

## Data and scale

SQLite keeps local development and tests self-contained. Production deployments
use PostgreSQL through `TOASTYANALYTICS_DB_URL`; the Docker stacks run Redis for
Celery, and the split-database stack provisions one database per service. The
API is stateless apart from the database, so it scales horizontally behind a load
balancer when the database and Redis are shared.

## Extension points

- **Custom graders:** implement `BaseGrader` and register the class in
  `toastyanalytics/plugins/custom/`; `plugin_loader.py` discovers it.
- **YAML rules:** add regex-based rules to
  `toastyanalytics/plugins/custom/example_rules.yaml`.
- **New dimensions:** add an enum member, a grader, and a factory mapping in
  `graders/__init__.py`.

## Testing

```bash
pytest                        # unit and integration tests
pytest --cov=toastyanalytics  # with coverage
```

`tests/test_graders.py` and `tests/test_text_graders.py` cover scoring behaviour,
`tests/test_meta_learning.py` covers strategy updates, `tests/test_auth.py`
covers credential and scope handling, `tests/test_rate_limiting.py` covers the
limiter, and `tests/test_integration.py` exercises the API through `TestClient`.
Tests that need a live server are marked and skipped by default.
