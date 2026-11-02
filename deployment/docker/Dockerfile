FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Build dependencies for wheels that do not ship binaries.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-prod.txt ./
RUN pip install -r requirements-prod.txt

COPY pyproject.toml README.md requirements.txt ./
COPY toastyanalytics/ ./toastyanalytics/
RUN pip install --no-cache-dir .

# Run as an unprivileged user.
RUN useradd --create-home --uid 1000 toasty \
    && chown -R toasty:toasty /app
USER toasty

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=3).raise_for_status()"

CMD ["uvicorn", "toastyanalytics.api:app", "--host", "0.0.0.0", "--port", "8000"]
