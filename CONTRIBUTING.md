# Contributing

Thanks for improving ToastyAnalytics. This guide covers the local workflow and
what a pull request should include.

## Development setup

Requires Python 3.10+ and Git. Docker is optional and only needed for the
PostgreSQL/Redis stacks.

```bash
git clone https://github.com/Lordbeatus/Toasty-Analytics.git
cd Toasty-Analytics

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

cp .env.example .env
pytest
uvicorn toastyanalytics.api:app --reload
```

The service runs on <http://localhost:8000> with an SQLite database by default.

## Making changes

1. Create a branch: `git checkout -b feature/your-feature`.
2. Make the change and add tests.
3. Run the checks below.
4. Commit with a conventional message and open a pull request.

### Checks

```bash
pytest
black --check toastyanalytics tests
isort --check-only --profile black toastyanalytics tests
flake8 toastyanalytics tests
```

CI runs the same commands on Python 3.10–3.13, plus Bandit and the MCP server's
JavaScript checks.

### Style

- Black formatting, isort with the Black profile, flake8 at 120 columns.
- Type hints on public functions and modules.
- Docstrings on public classes, modules, and non-obvious functions.
- Keep API responses and CLI output plain ASCII.

### Commit messages

Use conventional commits:

- `feat: add a language-aware complexity heuristic`
- `fix: return 400 for unsupported grading dimensions`
- `docs: correct the deployment prerequisites`
- `test: cover feedback-driven threshold updates`
- `refactor: split grader factories from implementations`

## Pull requests

Include:

- what changed and why
- the tests and commands you ran
- any configuration or migration notes

Keep pull requests focused. Unrelated formatting or refactors make review
slower; separate them into their own change.

## Reporting bugs

Open an issue with:

- Python version and operating system
- steps to reproduce
- expected and actual behaviour
- relevant logs or a minimal snippet

## Feature requests

Describe the use case, the proposed behaviour, and alternatives you considered.
Backward compatibility matters: note anything that would change the API or the
stored data.

## Code of conduct

Be respectful, assume good intent, and keep discussion focused on the work.
Harassment, discriminatory language, and personal attacks are not acceptable.

## Documentation

- [Documentation index](docs/README.md)
- [Architecture](docs/architecture.md)
- [Quick start](docs/quickstart.md)
- [Production deployment](docs/production-deployment.md)
