"""Application settings, read from the environment and a local .env file."""

import os
from typing import Optional

from dotenv import load_dotenv

# Read .env from the working directory, if present, before reading variables.
load_dotenv()


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    """Configuration management"""

    # Database
    DATABASE_URL: str = os.getenv(
        "TOASTYANALYTICS_DB_URL",
        "sqlite:///toastyanalytics.db",  # Default for development
    )

    # Redis (Celery broker and result backend)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Celery (background workers)
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv(
        "CELERY_RESULT_BACKEND", "redis://localhost:6379/1"
    )

    # Sentry (error tracking)
    SENTRY_DSN: Optional[str] = os.getenv("SENTRY_DSN")
    SENTRY_ENVIRONMENT: str = os.getenv("SENTRY_ENVIRONMENT", "development")

    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")  # nosec B104
    PORT: int = int(os.getenv("PORT", "8000"))
    WORKERS: int = int(os.getenv("WORKERS", "4"))

    # Monitoring
    PROMETHEUS_PORT: int = int(os.getenv("PROMETHEUS_PORT", "9090"))

    # Authentication
    AUTH_ENABLED: bool = _env_bool("AUTH_ENABLED", True)
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    API_KEY_HEADER: str = "X-API-Key"
    # key:user_id:roles:scopes, comma separated; "*" scope grants everything.
    API_KEYS: str = os.getenv("TOASTY_API_KEYS", "")

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = _env_bool("RATE_LIMIT_ENABLED", True)
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT", "60"))
    # Requests per minute for callers with the admin role; 0 disables the limit.
    RATE_LIMIT_ADMIN_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_ADMIN", "0"))


# Singleton instance
config = Config()


def get_settings() -> Config:
    """Get configuration settings"""
    return config
