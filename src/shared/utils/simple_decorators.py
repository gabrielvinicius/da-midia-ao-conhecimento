"""
Simplified decorators - replacing complex decorator system
"""
import logging
import functools
from typing import Any, Callable, Optional, Dict
import asyncio

logger = logging.getLogger(__name__)

def simple_logger(name: str = "operation"):
    """Simple logging decorator"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger.info(f"{name}: Starting {func.__name__}")
            try:
                result = await func(*args, **kwargs)
                logger.info(f"{name}: Completed {func.__name__}")
                return result
            except Exception as e:
                logger.error(f"{name}: Failed {func.__name__}: {e}")
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger.info(f"{name}: Starting {func.__name__}")
            try:
                result = func(*args, **kwargs)
                logger.info(f"{name}: Completed {func.__name__}")
                return result
            except Exception as e:
                logger.error(f"{name}: Failed {func.__name__}: {e}")
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

def simple_cache(ttl: int = 300):
    """Simple cache decorator"""
    cache: Dict[str, Any] = {}
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            key = f"{func.__name__}_{hash(str(args) + str(sorted(kwargs.items())))}"
            if key in cache:
                return cache[key]
            result = await func(*args, **kwargs)
            cache[key] = result
            return result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            key = f"{func.__name__}_{hash(str(args) + str(sorted(kwargs.items())))}"
            if key in cache:
                return cache[key]
            result = func(*args, **kwargs)
            cache[key] = result
            return result
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator