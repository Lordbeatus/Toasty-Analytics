"""
Sentry integration for error tracking

What is Sentry?
- Cloud service that catches errors/crashes
- Shows you stack traces, user context, etc.
- Free tier: 5k errors/month

Setup:
1. Sign up at sentry.io (free)
2. Create project → get DSN (looks like https://xxx@sentry.io/123)
3. Set env var: SENTRY_DSN=your_dsn_here
"""

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from src.config import config


def init_sentry():
    """
    Initialize Sentry error tracking.

    Only runs if SENTRY_DSN is set in environment.
    """
    if not config.SENTRY_DSN:
        print("ℹ️  Sentry disabled (no DSN configured)")
        return

    sentry_sdk.init(
        dsn=config.SENTRY_DSN,
        # Which environment (dev/staging/production)
        environment=config.SENTRY_ENVIRONMENT,
        # Integrations (auto-track errors from these libraries)
        integrations=[
            FastApiIntegration(),  # Track API errors
            CeleryIntegration(),  # Track background task errors
            RedisIntegration(),  # Track cache errors
            SqlalchemyIntegration(),  # Track database errors
        ],
        # Performance monitoring
        traces_sample_rate=0.1,  # Track 10% of requests for performance
        # What to send to Sentry
        send_default_pii=False,  # Don't send personal info
        # Error filtering
        before_send=filter_errors,
    )

    print(f"✅ Sentry initialized (env: {config.SENTRY_ENVIRONMENT})")


def filter_errors(event, hint):
    """
    Filter out errors we don't care about.

    Examples:
    - User sent invalid input (not our bug)
    - Network timeouts (not our fault)
    """
    # Ignore 404 errors
    if event.get("exception", {}).get("values", [{}])[0].get("type") == "NotFoundError":
        return None

    # Ignore user input errors
    if "ValidationError" in str(event):
        return None

    return event


def capture_grading_error(user_id: str, code_snippet: str, error: Exception):
    """
    Report a grading error to Sentry with context.

    Example:
        try:
            result = grader.grade(code)
        except Exception as e:
            capture_grading_error("user123", code[:100], e)
            raise
    """
    sentry_sdk.set_context(
        "grading",
        {
            "user_id": user_id,
            "code_length": len(code_snippet),
            "code_preview": (
                code_snippet[:100] + "..." if len(code_snippet) > 100 else code_snippet
            ),
        },
    )

    sentry_sdk.capture_exception(error)
