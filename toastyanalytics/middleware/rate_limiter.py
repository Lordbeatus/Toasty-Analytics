"""Rate limiting for the HTTP API.

Uses a Redis sorted-set sliding window when Redis is reachable and falls back to
an in-process sliding window otherwise. Limits are applied per caller and per
endpoint, with separate limits per role tier.
"""

import logging
import threading
import time
import uuid
from collections import defaultdict, deque
from functools import wraps
from typing import Callable, Deque, Dict, Optional, Tuple

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

try:  # Redis is optional for local development and tests.
    import redis
except ImportError:  # pragma: no cover - exercised only without the extra
    redis = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

EXEMPT_PATHS = frozenset({"/", "/health", "/docs", "/redoc", "/openapi.json"})


class InMemoryRateLimiter:
    """Thread-safe sliding-window limiter that needs no external service."""

    def __init__(self) -> None:
        self._buckets: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window: int) -> Tuple[bool, int, int]:
        """Record an attempt and return ``(allowed, remaining, reset_in)``."""
        now = time.time()
        cutoff = now - window
        with self._lock:
            bucket = self._buckets[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            allowed = len(bucket) < limit
            if allowed:
                bucket.append(now)
            remaining = max(0, limit - len(bucket))
            reset_in = int(bucket[0] + window - now) if bucket else window
            if not self._buckets[key]:
                del self._buckets[key]
            return allowed, remaining, max(1, reset_in)

    def reset(self, key: str) -> None:
        with self._lock:
            self._buckets.pop(key, None)


class RateLimiter:
    """
    Sliding-window rate limiter with Redis and in-memory backends.

    Counters are keyed by identifier (user or IP) and optionally endpoint, so a
    single caller gets an independent budget per route.
    """

    def __init__(
        self,
        redis_client: Optional[object] = None,
        default_limit: int = 60,
        default_window: int = 60,
        redis_url: Optional[str] = None,
    ):
        self.default_limit = default_limit
        self.default_window = default_window
        self._memory = InMemoryRateLimiter()
        self._redis_failed = False
        self._redis_url = redis_url
        self._connect_lock = threading.Lock()
        self.redis = redis_client

    def _ensure_redis(self) -> None:
        """Connect to Redis on first use instead of at import time."""
        if self.redis is not None or self._redis_failed:
            return
        if not self._redis_url or redis is None:
            return

        with self._connect_lock:
            if self.redis is not None or self._redis_failed:
                return
            try:
                client = redis.from_url(
                    self._redis_url,
                    socket_connect_timeout=1,
                    socket_timeout=1,
                    decode_responses=True,
                )
                client.ping()
                self.redis = client
            except Exception as exc:  # pragma: no cover - depends on environment
                self._redis_failed = True
                logger.warning(
                    "Redis unavailable (%s); rate limiting uses in-memory counters",
                    exc,
                )

    @property
    def backend(self) -> str:
        return "redis" if self.redis is not None else "memory"

    def _get_key(self, identifier: str, endpoint: Optional[str] = None) -> str:
        if endpoint:
            return f"ratelimit:{identifier}:{endpoint}"
        return f"ratelimit:{identifier}"

    def check_rate_limit(
        self,
        identifier: str,
        limit: Optional[int] = None,
        window: Optional[int] = None,
        endpoint: Optional[str] = None,
    ) -> Tuple[bool, dict]:
        """
        Check whether a request is allowed.

        Returns ``(allowed, info)`` where info has ``limit``, ``remaining``,
        ``reset``, ``reset_in``, and ``current_count``.
        """
        limit = self.default_limit if limit is None else limit
        window = self.default_window if window is None else window
        key = self._get_key(identifier, endpoint)
        self._ensure_redis()

        if self.redis is not None and not self._redis_failed:
            try:
                return self._check_redis(key, limit, window)
            except Exception as exc:  # pragma: no cover - depends on environment
                self._redis_failed = True
                logger.warning(
                    "Redis rate-limit check failed (%s); using in-memory counters",
                    exc,
                )

        return self._check_memory(key, limit, window)

    def _check_redis(self, key: str, limit: int, window: int) -> Tuple[bool, dict]:
        now = time.time()
        window_start = now - window
        member = f"{now}:{uuid.uuid4().hex}"

        pipe = self.redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zcard(key)
        pipe.zadd(key, {member: now})
        pipe.expire(key, window)
        results = pipe.execute()
        request_count = int(results[1])

        allowed = request_count < limit
        remaining = max(0, limit - request_count - 1)
        return allowed, {
            "limit": limit,
            "remaining": remaining,
            "reset": int(now + window),
            "reset_in": window,
            "current_count": request_count + 1,
            "backend": "redis",
        }

    def _check_memory(self, key: str, limit: int, window: int) -> Tuple[bool, dict]:
        allowed, remaining, reset_in = self._memory.check(key, limit, window)
        return allowed, {
            "limit": limit,
            "remaining": remaining,
            "reset": int(time.time() + reset_in),
            "reset_in": reset_in,
            "current_count": limit - remaining,
            "backend": "memory",
        }

    def reset_limit(self, identifier: str, endpoint: Optional[str] = None) -> None:
        """Clear the counter for an identifier."""
        key = self._get_key(identifier, endpoint)
        self._memory.reset(key)
        if self.redis is not None:
            try:
                self.redis.delete(key)
            except Exception as exc:  # pragma: no cover - depends on environment
                logger.warning("Failed to reset Redis rate limit: %s", exc)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    ASGI middleware that rate limits requests and emits standard headers.

    ``tier_resolver`` maps a request to a tier name; ``tier_limits`` maps tiers to
    ``(limit, window_seconds)``. A limit of ``None`` disables limiting for that
    tier. Unknown tiers use the limiter's defaults.
    """

    def __init__(
        self,
        app,
        rate_limiter: RateLimiter,
        identifier_callback: Optional[Callable[[Request], str]] = None,
        tier_resolver: Optional[Callable[[Request], str]] = None,
        tier_limits: Optional[Dict[str, Tuple[Optional[int], int]]] = None,
        exempt_paths: Optional[frozenset] = None,
    ):
        super().__init__(app)
        self.rate_limiter = rate_limiter
        self.identifier_callback = identifier_callback or self._default_identifier
        self.tier_resolver = tier_resolver or (lambda request: "default")
        self.tier_limits = tier_limits or {}
        self.exempt_paths = exempt_paths or EXEMPT_PATHS

    def _default_identifier(self, request: Request) -> str:
        if hasattr(request.state, "user_id"):
            return f"user:{request.state.user_id}"
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"

    def _limit_for(self, request: Request) -> Tuple[Optional[int], int]:
        tier = self.tier_resolver(request)
        if tier in self.tier_limits:
            return self.tier_limits[tier]
        return self.rate_limiter.default_limit, self.rate_limiter.default_window

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in self.exempt_paths or path.startswith("/docs"):
            return await call_next(request)

        limit, window = self._limit_for(request)
        if limit is None:
            return await call_next(request)

        identifier = self.identifier_callback(request)
        endpoint = f"{request.method}:{path}"
        allowed, info = self.rate_limiter.check_rate_limit(
            identifier=identifier, limit=limit, window=window, endpoint=endpoint
        )

        headers = {
            "X-RateLimit-Limit": str(info["limit"]),
            "X-RateLimit-Remaining": str(info["remaining"]),
            "X-RateLimit-Reset": str(info["reset"]),
        }

        if not allowed:
            headers["Retry-After"] = str(info["reset_in"])
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests. Please try again later.",
                    "limit": info["limit"],
                    "reset": info["reset"],
                    "reset_in": info["reset_in"],
                },
                headers=headers,
            )

        response = await call_next(request)
        response.headers.update(headers)
        return response


def rate_limit(limit: int = 100, window: int = 60, key_func: Optional[Callable] = None):
    """Decorator for endpoint-specific limits, using ``app.state.rate_limiter``."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = next((arg for arg in args if isinstance(arg, Request)), None)
            if request is None:
                request = kwargs.get("request")
            if request is None or not hasattr(request.app.state, "rate_limiter"):
                return await func(*args, **kwargs)

            limiter = request.app.state.rate_limiter
            identifier = (
                key_func(request)
                if key_func
                else f"ip:{request.client.host if request.client else 'unknown'}"
            )
            allowed, info = limiter.check_rate_limit(
                identifier=identifier,
                limit=limit,
                window=window,
                endpoint=f"{request.method}:{request.url.path}",
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
                        "Retry-After": str(info["reset_in"]),
                        "X-RateLimit-Limit": str(info["limit"]),
                        "X-RateLimit-Remaining": "0",
                    },
                )
            return await func(*args, **kwargs)

        return wrapper

    return decorator


class TieredRateLimiter(RateLimiter):
    """Rate limiter with named role tiers (free, basic, pro, enterprise)."""

    TIER_LIMITS = {
        "free": (100, 3600),
        "basic": (1000, 3600),
        "pro": (10000, 3600),
        "enterprise": (None, None),
    }

    def check_rate_limit_by_tier(
        self, identifier: str, tier: str, endpoint: Optional[str] = None
    ) -> Tuple[bool, dict]:
        tier = tier.lower()
        if tier == "enterprise":
            return True, {
                "limit": None,
                "remaining": None,
                "reset": None,
                "reset_in": None,
                "current_count": 0,
                "tier": tier,
            }

        limit, window = self.TIER_LIMITS.get(tier, self.TIER_LIMITS["free"])
        allowed, info = self.check_rate_limit(
            identifier=identifier, limit=limit, window=window, endpoint=endpoint
        )
        info["tier"] = tier
        return allowed, info


__all__ = [
    "EXEMPT_PATHS",
    "InMemoryRateLimiter",
    "RateLimitMiddleware",
    "RateLimiter",
    "TieredRateLimiter",
    "rate_limit",
]
