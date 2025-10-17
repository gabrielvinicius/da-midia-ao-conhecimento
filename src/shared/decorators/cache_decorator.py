"""
Cache Decorator for transparent caching
"""
import asyncio
import hashlib
import json
import time
from typing import Any, Optional, Dict, Callable
from dataclasses import dataclass
from .base_decorator import BaseAsyncDecorator


@dataclass
class CacheEntry:
    """Cache entry with TTL support"""
    value: Any
    created_at: float
    ttl_seconds: float
    hit_count: int = 0
    
    @property
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        if self.ttl_seconds <= 0:  # TTL of 0 means no expiration
            return False
        return time.time() - self.created_at > self.ttl_seconds
    
    def record_hit(self) -> None:
        """Record cache hit"""
        self.hit_count += 1


class CacheManager:
    """Thread-safe cache manager - Singleton Pattern"""
    
    _instance = None
    _cache: Dict[str, CacheEntry] = {}
    _stats = {
        "hits": 0,
        "misses": 0,
        "evictions": 0,
        "total_entries": 0
    }
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        entry = self._cache.get(key)
        
        if entry is None:
            self._stats["misses"] += 1
            return None
        
        if entry.is_expired:
            self._evict(key)
            self._stats["misses"] += 1
            return None
        
        entry.record_hit()
        self._stats["hits"] += 1
        return entry.value
    
    def set(self, key: str, value: Any, ttl_seconds: float = 300) -> None:
        """Set value in cache with TTL"""
        if key in self._cache:
            self._evict(key)
        
        self._cache[key] = CacheEntry(
            value=value,
            created_at=time.time(),
            ttl_seconds=ttl_seconds
        )
        self._stats["total_entries"] += 1
    
    def _evict(self, key: str) -> None:
        """Evict entry from cache"""
        if key in self._cache:
            del self._cache[key]
            self._stats["evictions"] += 1
    
    def clear(self) -> None:
        """Clear all cache entries"""
        evicted_count = len(self._cache)
        self._cache.clear()
        self._stats["evictions"] += evicted_count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            **self._stats,
            "current_entries": len(self._cache),
            "hit_rate_percent": round(hit_rate, 2),
            "total_requests": total_requests
        }
    
    def cleanup_expired(self) -> int:
        """Remove expired entries and return count"""
        expired_keys = [
            key for key, entry in self._cache.items() 
            if entry.is_expired
        ]
        
        for key in expired_keys:
            self._evict(key)
        
        return len(expired_keys)


class CacheDecorator(BaseAsyncDecorator):
    """Decorator for transparent function result caching"""
    
    def __init__(
        self,
        ttl_seconds: float = 300,  # 5 minutes default
        cache_key_builder: Optional[Callable] = None,
        cache_condition: Optional[Callable] = None,
        invalidate_on_error: bool = False
    ):
        super().__init__("cache")
        self.ttl_seconds = ttl_seconds
        self.cache_key_builder = cache_key_builder or self._default_key_builder
        self.cache_condition = cache_condition or (lambda *args, **kwargs: True)
        self.invalidate_on_error = invalidate_on_error
        self.cache_manager = CacheManager()
        self.cache_key = None
    
    async def _before_execution(self, *args, **kwargs) -> Optional[Any]:
        """Check cache before execution"""
        if not self.cache_condition(*args, **kwargs):
            return None
        
        self.cache_key = self.cache_key_builder(*args, **kwargs)
        cached_value = self.cache_manager.get(self.cache_key)
        
        if cached_value is not None:
            return cached_value
        
        return None
    
    async def _after_execution(self, result: Any, *args, **kwargs) -> Any:
        """Cache result after successful execution"""
        if self.cache_key and result is not None:
            self.cache_manager.set(self.cache_key, result, self.ttl_seconds)
        
        return result
    
    async def _on_exception(self, exception: Exception, *args, **kwargs) -> None:
        """Handle cache on exceptions"""
        if self.invalidate_on_error and self.cache_key:
            self.cache_manager._evict(self.cache_key)
    
    def _default_key_builder(self, *args, **kwargs) -> str:
        """Build cache key from function arguments"""
        # Create a stable hash from arguments
        key_data = {
            "args": self._serialize_args(args),
            "kwargs": self._serialize_kwargs(kwargs)
        }
        
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _serialize_args(self, args: tuple) -> list:
        """Serialize args for cache key"""
        serialized = []
        for arg in args:
            if hasattr(arg, 'id'):
                serialized.append(f"obj_id:{arg.id}")
            elif isinstance(arg, (str, int, float, bool, type(None))):
                serialized.append(arg)
            else:
                serialized.append(f"obj_type:{type(arg).__name__}")
        return serialized
    
    def _serialize_kwargs(self, kwargs: dict) -> dict:
        """Serialize kwargs for cache key"""
        serialized = {}
        for key, value in kwargs.items():
            if hasattr(value, 'id'):
                serialized[key] = f"obj_id:{value.id}"
            elif isinstance(value, (str, int, float, bool, type(None))):
                serialized[key] = value
            else:
                serialized[key] = f"obj_type:{type(value).__name__}"
        return serialized


class SmartCacheDecorator(CacheDecorator):
    """Smart cache with adaptive TTL and invalidation patterns"""
    
    def __init__(
        self,
        base_ttl_seconds: float = 300,
        max_ttl_seconds: float = 3600,
        hit_threshold_for_extension: int = 5
    ):
        super().__init__(ttl_seconds=base_ttl_seconds)
        self.base_ttl_seconds = base_ttl_seconds
        self.max_ttl_seconds = max_ttl_seconds
        self.hit_threshold_for_extension = hit_threshold_for_extension
    
    async def _before_execution(self, *args, **kwargs) -> Optional[Any]:
        """Enhanced cache lookup with adaptive TTL"""
        if not self.cache_condition(*args, **kwargs):
            return None
        
        self.cache_key = self.cache_key_builder(*args, **kwargs)
        entry = self.cache_manager._cache.get(self.cache_key)
        
        if entry is None:
            self.cache_manager._stats["misses"] += 1
            return None
        
        if entry.is_expired:
            self.cache_manager._evict(self.cache_key)
            self.cache_manager._stats["misses"] += 1
            return None
        
        # Adaptive TTL: extend TTL for frequently accessed items
        if entry.hit_count >= self.hit_threshold_for_extension:
            new_ttl = min(entry.ttl_seconds * 1.5, self.max_ttl_seconds)
            entry.ttl_seconds = new_ttl
        
        entry.record_hit()
        self.cache_manager._stats["hits"] += 1
        return entry.value