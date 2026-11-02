"""Rate limiting tests (in-memory backend; no Redis required)."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from toastyanalytics.middleware.rate_limiter import (
    InMemoryRateLimiter,
    RateLimiter,
    RateLimitMiddleware,
    TieredRateLimiter,
)


def build_app(limits):
    test_app = FastAPI()
    limiter = RateLimiter(default_limit=2, default_window=60)

    test_app.add_middleware(
        RateLimitMiddleware,
        rate_limiter=limiter,
        tier_limits=limits,
    )

    @test_app.get("/thing")
    async def thing():
        return {"ok": True}

    @test_app.get("/other")
    async def other():
        return {"ok": True}

    @test_app.get("/health")
    async def health():
        return {"ok": True}

    return test_app


class TestInMemoryLimiter:
    def test_allows_up_to_limit_then_denies(self):
        limiter = InMemoryRateLimiter()

        allowed, remaining, _ = limiter.check("user:1", 2, 60)
        assert allowed is True
        assert remaining == 1

        allowed, remaining, _ = limiter.check("user:1", 2, 60)
        assert allowed is True
        assert remaining == 0

        allowed, remaining, _ = limiter.check("user:1", 2, 60)
        assert allowed is False
        assert remaining == 0

    def test_counters_are_isolated_per_key(self):
        limiter = InMemoryRateLimiter()
        limiter.check("user:1", 1, 60)
        allowed, _, _ = limiter.check("user:2", 1, 60)
        assert allowed is True

    def test_reset_clears_counter(self):
        limiter = InMemoryRateLimiter()
        limiter.check("user:1", 1, 60)
        limiter.reset("user:1")
        allowed, _, _ = limiter.check("user:1", 1, 60)
        assert allowed is True


class TestRateLimiter:
    def test_defaults_to_memory_without_redis(self):
        limiter = RateLimiter(default_limit=1)
        allowed, info = limiter.check_rate_limit("user:1")
        assert allowed is True
        assert info["backend"] == "memory"
        assert info["limit"] == 1

        allowed, info = limiter.check_rate_limit("user:1")
        assert allowed is False
        assert info["remaining"] == 0


class TestMiddleware:
    def test_returns_429_with_retry_headers(self):
        client = TestClient(build_app({"default": (2, 60)}))

        assert client.get("/thing").status_code == 200
        assert client.get("/thing").status_code == 200
        response = client.get("/thing")

        assert response.status_code == 429
        assert response.headers["x-ratelimit-limit"] == "2"
        assert response.headers["x-ratelimit-remaining"] == "0"
        assert int(response.headers["retry-after"]) > 0
        assert response.json()["error"] == "rate_limit_exceeded"

    def test_limit_headers_present_on_success(self):
        client = TestClient(build_app({"default": (5, 60)}))
        response = client.get("/thing")
        assert response.headers["x-ratelimit-limit"] == "5"
        assert response.headers["x-ratelimit-remaining"] == "4"

    def test_health_is_exempt(self):
        client = TestClient(build_app({"default": (1, 60)}))
        for _ in range(5):
            assert client.get("/health").status_code == 200

    def test_endpoints_have_separate_budgets(self):
        client = TestClient(build_app({"default": (1, 60)}))
        assert client.get("/thing").status_code == 200
        assert client.get("/other").status_code == 200
        assert client.get("/thing").status_code == 429

    def test_unlimited_tier_is_never_blocked(self):
        client = TestClient(build_app({"default": (1, 60), "admin": (None, 60)}))

        # Default tier blocks after one request.
        assert client.get("/thing").status_code == 200
        assert client.get("/thing").status_code == 429


class TestTieredLimiter:
    def test_enterprise_is_unlimited(self):
        limiter = TieredRateLimiter()
        allowed, info = limiter.check_rate_limit_by_tier("user:1", "enterprise")
        assert allowed is True
        assert info["limit"] is None

    def test_unknown_tier_falls_back_to_free_limits(self):
        limiter = TieredRateLimiter()
        allowed, info = limiter.check_rate_limit_by_tier("user:1", "unknown")
        assert allowed is True
        assert info["limit"] == TieredRateLimiter.TIER_LIMITS["free"][0]
