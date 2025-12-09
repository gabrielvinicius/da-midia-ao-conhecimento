"""Fallback cache implementation when Redis is not available."""

import json
import time
from typing import Any, Dict, Optional
from src.shared.infrastructure.observability.logging.logging_config import get_logger

logger = get_logger("cache")


class FallbackCache:
    """Fallback cache implementation using in-memory storage."""

    def __init__(self):
        self._cache: Dict[str, tuple] = {}  # key -> (value, expiration_timestamp)
        self.is_connected = True  # Always considered connected for fallback

    async def connect(self):
        """Connect method (no-op for fallback cache)."""
        logger.info("Using fallback cache (in-memory) - Redis not available")
        self.is_connected = True

    async def disconnect(self):
        """Disconnect method (cleanup in-memory cache)."""
        self._cache.clear()
        self.is_connected = False
        logger.info("Fallback cache disconnected")

    def _generate_key(self, prefix: str, key: str, **kwargs) -> str:
        """Generate standardized cache key."""
        base_key = f"{prefix}{key}"

        # Add extra parameters if provided
        if kwargs:
            # Sort kwargs for consistency
            sorted_params = sorted(kwargs.items())
            params_str = "&".join(f"{k}={v}" for k, v in sorted_params)
            base_key = f"{base_key}?{params_str}"

        return base_key

    async def get(self, prefix: str, key: str, **kwargs) -> Optional[Any]:
        """Get value from cache."""
        cache_key = self._generate_key(prefix, key, **kwargs)

        try:
            if cache_key in self._cache:
                value, expiry = self._cache[cache_key]
                if expiry is None or time.time() < expiry:
                    logger.debug("Fallback cache hit", key=cache_key)
                    return value

            logger.debug("Fallback cache miss", key=cache_key)
            return None

        except Exception as e:
            logger.warning("Fallback cache get error", extra={"key": cache_key, "error": str(e)})
            return None

    async def set(
        self,
        prefix: str,
        key: str,
        value: Any,
        ttl: int = 300,  # 5 minutes default
        **kwargs
    ) -> bool:
        """Set value in cache."""
        cache_key = self._generate_key(prefix, key, **kwargs)

        try:
            expiry = time.time() + ttl if ttl > 0 else None
            self._cache[cache_key] = (value, expiry)

            logger.debug("Fallback cache set", key=cache_key, ttl=ttl)
            return True

        except Exception as e:
            logger.error("Fallback cache set error", extra={"key": cache_key, "error": str(e)})
            return False

    async def delete(self, prefix: str, key: str, **kwargs) -> bool:
        """Remove value from cache."""
        cache_key = self._generate_key(prefix, key, **kwargs)

        try:
            if cache_key in self._cache:
                del self._cache[cache_key]
                logger.debug("Fallback cache delete", key=cache_key)
                return True

            return False

        except Exception as e:
            logger.error("Fallback cache delete error", extra={"key": cache_key, "error": str(e)})
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Remove multiple keys by pattern."""
        try:
            deleted_count = 0
            keys_to_delete = []

            for key in self._cache:
                if pattern in key:
                    keys_to_delete.append(key)

            for key in keys_to_delete:
                del self._cache[key]
                deleted_count += 1

            logger.info("Fallback cache pattern delete", pattern=pattern, deleted=deleted_count)
            return deleted_count

        except Exception as e:
            logger.error("Fallback cache pattern delete error", extra={"pattern": pattern, "error": str(e)})
            return 0

    async def check_rate_limit(self, key: str, limit: int, window: int = 60) -> dict:
        """Check rate limit for a given key."""
        try:
            current_time = int(time.time())
            window_start = current_time - window

            # Use a simple counter approach for fallback
            counter_key = f"rate_limit:{key}"
            if counter_key in self._cache:
                counter_data, expiry = self._cache[counter_key]
                # Clean old entries
                recent_calls = [call_time for call_time in counter_data if call_time > window_start]
            else:
                recent_calls = []

            recent_calls.append(current_time)
            # Keep only recent calls within window
            recent_calls = [call_time for call_time in recent_calls if call_time > window_start]

            # Update counter
            await self.set(counter_key, recent_calls, window)

            current_count = len(recent_calls)
            is_limited = current_count > limit
            remaining = max(0, limit - current_count)

            return {
                "allowed": not is_limited,
                "count": current_count,
                "remaining": remaining,
                "reset_time": current_time + window
            }

        except Exception as e:
            logger.error("Fallback rate limit check error", extra={"key": key, "error": str(e)})
            # Fail open - allow the request if cache is down
            return {
                "allowed": True,
                "count": 0,
                "remaining": limit,
                "reset_time": int(time.time()) + window
            }

    async def increment(self, prefix: str, key: str, amount: int = 1, ttl: int = 300, **kwargs) -> int:
        """Increment a counter in cache."""
        cache_key = self._generate_key(prefix, key, **kwargs)

        try:
            current_value = await self.get(prefix, key, **kwargs)
            if current_value is None:
                current_value = 0

            new_value = current_value + amount
            await self.set(prefix, key, new_value, ttl, **kwargs)

            return new_value

        except Exception as e:
            logger.error("Fallback cache increment error", extra={"key": cache_key, "error": str(e)})
            return 0


# Try to import RedisCache, fall back to FallbackCache if unavailable
try:
    from .cache import RedisCache as _RedisCache
    import redis.asyncio as _aioredis
    # Test if Redis settings are functional
    _test_cache = _RedisCache()
    cache = _test_cache
except Exception:
    # Fallback to in-memory cache if Redis is unavailable
    cache = FallbackCache()