# Documentation

ToastyAnalytics grades source code and adapts its scoring from feedback. This
directory covers installation, architecture, and deployment.

| Document | Contents |
| --- | --- |
| [quickstart.md](quickstart.md) | Install, run locally, configure, and operate the service |
| [architecture.md](architecture.md) | Components, data flow, and extension points |
| [production-deployment.md](production-deployment.md) | Docker, Kubernetes, and hosted deployment |

For a project overview and API summary, see the [root README](../README.md).

## Concepts

### Grading dimensions

A grading run takes a code snippet and one or more dimensions. Each dimension has
a grader that returns a `GraderResult` with a score, a breakdown, free-text
feedback, and improvement suggestions.

| Dimension | Grader | What it measures |
| --- | --- | --- |
| `code_quality` | `CodeQualityGraderV2` | Structure, readability, best practices, cyclomatic complexity |
| `readability` | `CodeQualityGraderV2` | The readability component of the code-quality analysis |
| `speed` | `SpeedGrader` | Generation and execution time against a target |
| `reliability` | `ReliabilityGrader` | Success rate and consistency across attempts |

Python snippets are parsed with `ast`, so structural scores come from real syntax
analysis rather than pattern matching. Other languages use the text-based
heuristics in the same graders.

### Meta-learning

Every grading is stored in `grading_history`. Feedback on a grading (a 1–5
rating plus optional comments) is passed to the meta-learner, which adjusts the
user's dimension weights and thresholds. Later gradings for that user apply the
learned strategy, so scoring converges on what the user considers useful.

### Feedback loop

1. `POST /grade` grades the snippet and stores the result with a `grading_id`.
2. `POST /feedback` records a rating for that `grading_id`.
3. The meta-learner updates the user's strategy.
4. The next `POST /grade` for the user applies the updated weights and thresholds.

### Events

The API pushes grading and learning events over `/ws/{user_id}`. Inside the
process, `toastyanalytics/messaging/` can deliver the same events over Kafka or
RabbitMQ when a broker is configured, and otherwise keeps them in memory.

## Conventions

- Python 3.10+, formatted with Black, imports sorted with isort, linted with
  flake8 (see `pyproject.toml` and `.flake8`).
- Runtime dependencies live in `requirements.txt`; development tooling in
  `requirements-dev.txt`; production extras in `requirements-prod.txt`.
- Tests use pytest with an in-memory SQLite database (`tests/conftest.py`).
