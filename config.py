"""
Production configuration for ToastyAnalytics
Set these in your .env file or environment variables
"""

import os
from typing import Optional


class Config:
    """Configuration management"""

    # Database
    DATABASE_URL: str = os.getenv(
        "TOASTYANALYTICS_DB_URL",
        "sqlite:///toastyanalytics.db",  # Default for development
    )

    # Redis (for caching and Celery)
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
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    WORKERS: int = int(os.getenv("WORKERS", "4"))

    # Caching
    ENABLE_CACHE: bool = os.getenv("ENABLE_CACHE", "true").lower() == "true"
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "3600"))  # 1 hour

    # Monitoring
    PROMETHEUS_PORT: int = int(os.getenv("PROMETHEUS_PORT", "9090"))
    ENABLE_METRICS: bool = os.getenv("ENABLE_METRICS", "true").lower() == "true"

    # Security
    API_KEY_HEADER: str = "X-API-Key"
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT", "60"))


# Singleton instance
config = Config()


def get_settings() -> Config:
    """Get configuration settings"""
    return config
