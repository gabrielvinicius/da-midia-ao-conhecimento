"""
Base decorator interface following Decorator Pattern
"""
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional
from functools import wraps
import asyncio
import inspect


class IServiceDecorator(ABC):
    """Base interface for service decorators - Decorator Pattern"""
    
    @abstractmethod
    def decorate(self, func: Callable) -> Callable:
        """Decorate a function with cross-cutting concerns."""
        pass


class BaseAsyncDecorator(IServiceDecorator):
    """Base implementation for async service decorators"""
    
    def __init__(self, name: str):
        self.name = name
    
    def decorate(self, func: Callable) -> Callable:
        """Apply decoration to async or sync functions"""
        
        if asyncio.iscoroutinefunction(func):
            return self._decorate_async(func)
        else:
            return self._decorate_sync(func)
    
    @abstractmethod
    async def _before_execution(self, *args, **kwargs) -> Optional[Any]:
        """Execute before the original function"""
        pass
    
    @abstractmethod
    async def _after_execution(self, result: Any, *args, **kwargs) -> Any:
        """Execute after successful function execution"""
        return result
    
    @abstractmethod
    async def _on_exception(self, exception: Exception, *args, **kwargs) -> None:
        """Handle exceptions during execution"""
        pass
    
    def _decorate_async(self, func: Callable) -> Callable:
        """Decorate async function"""
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                # Pre-execution hook
                pre_result = await self._before_execution(*args, **kwargs)
                if pre_result is not None:
                    return pre_result
                
                # Execute original function
                result = await func(*args, **kwargs)
                
                # Post-execution hook
                final_result = await self._after_execution(result, *args, **kwargs)
                return final_result
                
            except Exception as e:
                await self._on_exception(e, *args, **kwargs)
                raise
        
        return async_wrapper
    
    def _decorate_sync(self, func: Callable) -> Callable:
        """Decorate sync function"""
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                # Pre-execution hook (convert to sync)
                pre_result = asyncio.run(self._before_execution(*args, **kwargs))
                if pre_result is not None:
                    return pre_result
                
                # Execute original function
                result = func(*args, **kwargs)
                
                # Post-execution hook (convert to sync)
                final_result = asyncio.run(self._after_execution(result, *args, **kwargs))
                return final_result
                
            except Exception as e:
                asyncio.run(self._on_exception(e, *args, **kwargs))
                raise
        
        return sync_wrapper


class CompositeDecorator(IServiceDecorator):
    """Composite decorator to chain multiple decorators"""
    
    def __init__(self, decorators: list[IServiceDecorator]):
        self.decorators = decorators
    
    def decorate(self, func: Callable) -> Callable:
        """Apply multiple decorators in sequence"""
        decorated_func = func
        
        # Apply decorators in reverse order (last decorator wraps first)
        for decorator in reversed(self.decorators):
            decorated_func = decorator.decorate(decorated_func)
        
        return decorated_func