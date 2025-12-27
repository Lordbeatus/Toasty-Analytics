"""
Redis caching layer for ToastyAnalytics
Caches grading results for frequently seen code patterns
"""

import hashlib
import json
from typing import Any, Optional

import redis
from config import config


class CacheManager:
    """
    Manages Redis cache for grading results.

    Why we cache:
    - AI models often generate similar code patterns
    - Grading can be expensive (complexity analysis, etc.)
    - Cache = instant results for repeated patterns
    """

    def __init__(self):
        """
        Connect to Redis server.
        Redis = in-memory database (super fast key-value store)
        """
        try:
            self.redis_client = redis.from_url(
                config.REDIS_URL, decode_responses=True, socket_connect_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            self.enabled = config.ENABLE_CACHE
        except (redis.ConnectionError, redis.TimeoutError):
            print("⚠️  Redis not available - caching disabled")
            self.redis_client = None
            self.enabled = False

    def _generate_cache_key(self, code: str, language: str, dimension: str) -> str:
        """
        Generate unique key for this code.

        How it works:
        1. Combine code + language + dimension
        2. Hash it (SHA256) to get unique ID
        3. Use as Redis key

        Example: "grade:a3f2b9c..."
        """
        # Normalize code (remove extra whitespace)
        normalized = " ".join(code.split())

        # Create unique identifier
        content = f"{normalized}:{language}:{dimension}"
        hash_key = hashlib.sha256(content.encode()).hexdigest()

        return f"grade:{hash_key}"

    def get(self, code: str, language: str, dimension: str) -> Optional[dict]:
        """
        Try to get cached grading result.

        Returns:
            Cached result if found, None if not cached
        """
        if not self.enabled or not self.redis_client:
            return None

        try:
            key = self._generate_cache_key(code, language, dimension)
            cached = self.redis_client.get(key)

            if cached:
                # Found in cache! Return it
                return json.loads(cached)

            return None

        except Exception as e:
            print(f"Cache get error: {e}")
            return None

    def set(
        self,
        code: str,
        language: str,
        dimension: str,
        result: dict,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Store grading result in cache.

        Args:
            ttl: Time to live in seconds (how long to keep cached)
                 Default: 1 hour (3600 seconds)

        Returns:
            True if cached successfully
        """
        if not self.enabled or not self.redis_client:
            return False

        try:
            key = self._generate_cache_key(code, language, dimension)
            value = json.dumps(result)

            # Store with expiration time
            self.redis_client.setex(key, ttl or config.CACHE_TTL, value)

            return True

        except Exception as e:
            print(f"Cache set error: {e}")
            return False

    def invalidate_user(self, user_id: str):
        """
        Clear all cached results for a user.

        When to use:
        - User's learning strategies changed
        - User requested fresh grading
        """
        if not self.enabled or not self.redis_client:
            return

        try:
            # Find all keys for this user
            pattern = f"grade:*:user:{user_id}:*"
            keys = self.redis_client.keys(pattern)

            if keys:
                self.redis_client.delete(*keys)

        except Exception as e:
            print(f"Cache invalidate error: {e}")

    def clear_all(self):
        """Clear entire cache (use carefully!)"""
        if self.enabled and self.redis_client:
            self.redis_client.flushdb()

    def get_stats(self) -> dict:
        """Get cache statistics"""
        if not self.enabled or not self.redis_client:
            return {"enabled": False}

        try:
            info = self.redis_client.info("stats")
            return {
                "enabled": True,
                "total_keys": self.redis_client.dbsize(),
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "hit_rate": info.get("keyspace_hits", 0)
                / max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 1), 1)
                * 100,
            }
        except Exception as e:
            return {"enabled": True, "error": str(e)}


# Singleton instance
cache = CacheManager()
