# Examples

Three runnable examples. Install the package from the repository root first:

```bash
pip install -e .
```

## basic_usage.py

Uses the library directly: code-quality grading, meta-learning from feedback,
multiple dimensions, custom weights, and line-level feedback.

```bash
python examples/basic_usage.py
```

It writes to an in-memory database, so it needs no server.

## api_usage.py

Exercises the HTTP API: token exchange, grading, feedback, user analytics,
dimensions, and the health endpoint.

```bash
cp .env.example .env                            # defines the dev API key
uvicorn toastyanalytics.api:app --port 8000     # terminal 1
python examples/api_usage.py                    # terminal 2
```

The example reads `TOASTY_API_KEY` (default `dev-local-key`, as set in
`.env.example`) and exchanges it for a JWT at `POST /auth/token`.

Set `TOASTY_API_URL` to target another host or port:

```bash
TOASTY_API_URL=http://localhost:8123 TOASTY_API_KEY=your-key python examples/api_usage.py
```

## sample_code.py

Generates `good_code.py`, `bad_code.py`, and `medium_code.py` in the current
directory, then prints the CLI command to grade them.

```bash
python examples/sample_code.py
toastyanalytics grade good_code.py --user-id demo -d code_quality
```

## Where to go next

- [Quick start](../docs/quickstart.md) — installation and configuration
- [Architecture](../docs/architecture.md) — how grading and meta-learning fit together
- [API reference](http://localhost:8000/docs) — interactive OpenAPI docs
