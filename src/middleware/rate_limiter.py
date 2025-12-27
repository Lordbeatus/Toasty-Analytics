"""
Rate Limiting Middleware for ToastyAnalytics

Implements Redis-based rate limiting to prevent API abuse.
Supports per-user, per-IP, and per-endpoint rate limiting.
"""

import logging
import time
from functools import wraps
from typing import Callable, Optional

import redis
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Redis-based rate limiter with sliding window algorithm.

    Features:
    - Per-user rate limiting
    - Per-IP rate limiting
    - Per-endpoint rate limiting
    - Configurable time windows
    - Automatic key expiration
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        default_limit: int = 100,
        default_window: int = 60,
    ):
        """
        Initialize rate limiter.

        Args:
            redis_client: Redis client instance
            default_limit: Default number of requests allowed per window
            default_window: Default time window in seconds
        """
        self.redis = redis_client
        self.default_limit = default_limit
        self.default_window = default_window

    def _get_key(self, identifier: str, endpoint: Optional[str] = None) -> str:
        """Generate Redis key for rate limiting"""
        if endpoint:
            return f"ratelimit:{identifier}:{endpoint}"
        return f"ratelimit:{identifier}"

    def check_rate_limit(
        self,
        identifier: str,
        limit: Optional[int] = None,
        window: Optional[int] = None,
        endpoint: Optional[str] = None,
    ) -> tuple[bool, dict]:
        """
        Check if request is within rate limit.

        Args:
            identifier: Unique identifier (user_id, IP, etc.)
            limit: Maximum requests allowed
            window: Time window in seconds
            endpoint: Optional endpoint name for granular limiting

        Returns:
            Tuple of (allowed: bool, info: dict)
            info contains: remaining, reset_time, limit
        """
        limit = limit or self.default_limit
        window = window or self.default_window
        key = self._get_key(identifier, endpoint)

        try:
            current_time = int(time.time())
            window_start = current_time - window

            # Use sorted set to track requests in time window
            pipe = self.redis.pipeline()

            # Remove old requests outside the window
            pipe.zremrangebyscore(key, 0, window_start)

            # Count requests in current window
            pipe.zcard(key)

            # Add current request
            pipe.zadd(key, {str(current_time): current_time})

            # Set expiration
            pipe.expire(key, window)

            results = pipe.execute()
            request_count = results[1]

            # Check if limit exceeded
            allowed = request_count < limit
            remaining = max(0, limit - request_count - 1)
            reset_time = current_time + window

            return allowed, {
                "limit": limit,
                "remaining": remaining,
                "reset": reset_time,
                "reset_in": window,
                "current_count": request_count + 1,
            }

        except redis.RedisError as e:
            logger.error(f"Rate limit check failed: {e}")
            # Fail open - allow request if Redis is down
            return True, {
                "limit": limit,
                "remaining": limit,
                "reset": int(time.time() + window),
                "reset_in": window,
                "current_count": 0,
                "error": "rate_limiter_unavailable",
            }

    def reset_limit(self, identifier: str, endpoint: Optional[str] = None):
        """Reset rate limit for an identifier"""
        key = self._get_key(identifier, endpoint)
        try:
            self.redis.delete(key)
        except redis.RedisError as e:
            logger.error(f"Failed to reset rate limit: {e}")


class RateLimitMiddleware:
    """
    FastAPI middleware for automatic rate limiting.
    """

    def __init__(
        self, rate_limiter: RateLimiter, identifier_callback: Optional[Callable] = None
    ):
        """
        Initialize middleware.

        Args:
            rate_limiter: RateLimiter instance
            identifier_callback: Optional callback to extract identifier from request
        """
        self.rate_limiter = rate_limiter
        self.identifier_callback = identifier_callback or self._default_identifier

    def _default_identifier(self, request: Request) -> str:
        """Default identifier extraction (uses client IP)"""
        # Try to get user_id from request state (set by auth middleware)
        if hasattr(request.state, "user_id"):
            return f"user:{request.state.user_id}"

        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0]}"

        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"

    async def __call__(self, request: Request, call_next):
        """Process request with rate limiting"""
        identifier = self.identifier_callback(request)
        endpoint = f"{request.method}:{request.url.path}"

        # Check rate limit
        allowed, info = self.rate_limiter.check_rate_limit(
            identifier=identifier, endpoint=endpoint
        )

        # Add rate limit headers to response
        async def add_headers(response):
            response.headers["X-RateLimit-Limit"] = str(info["limit"])
            response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
            response.headers["X-RateLimit-Reset"] = str(info["reset"])
            return response

        if not allowed:
            # Rate limit exceeded
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests. Please try again later.",
                    "limit": info["limit"],
                    "reset": info["reset"],
                    "reset_in": info["reset_in"],
                },
                headers={
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(info["reset"]),
                    "Retry-After": str(info["reset_in"]),
                },
            )

        # Process request
        response = await call_next(request)
        return await add_headers(response)


# Decorator for endpoint-specific rate limiting


def rate_limit(limit: int = 100, window: int = 60, key_func: Optional[Callable] = None):
    """
    Decorator for endpoint-specific rate limiting.

    Usage:
        @app.post("/grade")
        @rate_limit(limit=10, window=60)
        async def grade_code(request: Request):
            return {"result": "graded"}

    Args:
        limit: Maximum requests allowed
        window: Time window in seconds
        key_func: Optional function to extract identifier from request
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find request object in args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                request = kwargs.get("request")

            if not request:
                # No request found, skip rate limiting
                return await func(*args, **kwargs)

            # Get rate limiter from app state
            if hasattr(request.app.state, "rate_limiter"):
                rate_limiter = request.app.state.rate_limiter
            else:
                # No rate limiter configured, skip
                return await func(*args, **kwargs)

            # Get identifier
            if key_func:
                identifier = key_func(request)
            else:
                # Default: use IP address
                identifier = (
                    f"ip:{request.client.host if request.client else 'unknown'}"
                )

            # Check rate limit
            endpoint = f"{request.method}:{request.url.path}"
            allowed, info = rate_limiter.check_rate_limit(
                identifier=identifier, limit=limit, window=window, endpoint=endpoint
            )

            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "rate_limit_exceeded",
                        "message": "Too many requests. Please try again later.",
                        "limit": info["limit"],
                        "reset": info["reset"],
                        "reset_in": info["reset_in"],
                    },
                    headers={
                        "X-RateLimit-Limit": str(info["limit"]),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(info["reset"]),
                        "Retry-After": str(info["reset_in"]),
                    },
                )

            # Execute endpoint
            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Tiered rate limiting


class TieredRateLimiter(RateLimiter):
    """
    Rate limiter with different limits for different user tiers.

    Tiers:
    - free: 100 requests/hour
    - basic: 1000 requests/hour
    - pro: 10000 requests/hour
    - enterprise: unlimited
    """

    TIER_LIMITS = {
        "free": (100, 3600),  # 100 requests per hour
        "basic": (1000, 3600),  # 1000 requests per hour
        "pro": (10000, 3600),  # 10000 requests per hour
        "enterprise": (None, None),  # Unlimited
    }

    def check_rate_limit_by_tier(
        self, identifier: str, tier: str, endpoint: Optional[str] = None
    ) -> tuple[bool, dict]:
        """
        Check rate limit based on user tier.

        Args:
            identifier: Unique identifier
            tier: User tier (free, basic, pro, enterprise)
            endpoint: Optional endpoint name

        Returns:
            Tuple of (allowed: bool, info: dict)
        """
        tier = tier.lower()

        # Enterprise tier has no limits
        if tier == "enterprise":
            return True, {
                "limit": None,
                "remaining": None,
                "reset": None,
                "reset_in": None,
                "current_count": 0,
                "tier": tier,
            }

        # Get tier limits
        limit, window = self.TIER_LIMITS.get(tier, self.TIER_LIMITS["free"])

        return self.check_rate_limit(
            identifier=identifier, limit=limit, window=window, endpoint=endpoint
        )
