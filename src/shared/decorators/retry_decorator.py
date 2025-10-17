"""
Retry Decorator for automatic failure recovery
"""
import asyncio
import random
import time
from typing import Any, Optional, Callable, Type, Tuple
from dataclasses import dataclass
from .base_decorator import BaseAsyncDecorator


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    exponential_backoff: bool = True
    jitter: bool = True
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)


class RetryDecorator(BaseAsyncDecorator):
    """Decorator for automatic retry with backoff strategies"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay_seconds: float = 1.0,
        max_delay_seconds: float = 60.0,
        exponential_backoff: bool = True,
        jitter: bool = True,
        retryable_exceptions: Tuple[Type[Exception], ...] = None,
        retry_condition: Optional[Callable] = None
    ):
        super().__init__("retry")
        self.config = RetryConfig(
            max_attempts=max_attempts,
            base_delay_seconds=base_delay_seconds,
            max_delay_seconds=max_delay_seconds,
            exponential_backoff=exponential_backoff,
            jitter=jitter,
            retryable_exceptions=retryable_exceptions or (Exception,)
        )
        self.retry_condition = retry_condition
        self.attempt_count = 0
        self.original_function = None
    
    def decorate(self, func: Callable) -> Callable:
        """Enhanced decoration with retry logic"""
        self.original_function = func
        return super().decorate(func)
    
    async def _before_execution(self, *args, **kwargs) -> Optional[Any]:
        """Prepare for retry attempt"""
        self.attempt_count = 0
        return None
    
    async def _after_execution(self, result: Any, *args, **kwargs) -> Any:
        """Return result on successful execution"""
        return result
    
    async def _on_exception(self, exception: Exception, *args, **kwargs) -> None:
        """Handle retry logic on exceptions"""
        # Check if exception is retryable
        if not self._is_retryable_exception(exception):
            raise exception
        
        # Check if we should retry based on custom condition
        if self.retry_condition and not self.retry_condition(exception, self.attempt_count):
            raise exception
        
        # Check if we've exceeded max attempts
        if self.attempt_count >= self.config.max_attempts:
            raise exception
        
        # Calculate delay and retry
        delay = self._calculate_delay()
        await asyncio.sleep(delay)
        
        # Retry the original function
        try:
            self.attempt_count += 1
            if asyncio.iscoroutinefunction(self.original_function):
                result = await self.original_function(*args, **kwargs)
            else:
                result = self.original_function(*args, **kwargs)
            
            # If we get here, the retry succeeded
            return result
            
        except Exception as retry_exception:
            # Recursively handle the retry exception
            await self._on_exception(retry_exception, *args, **kwargs)
    
    def _is_retryable_exception(self, exception: Exception) -> bool:
        """Check if exception is retryable"""
        return isinstance(exception, self.config.retryable_exceptions)
    
    def _calculate_delay(self) -> float:
        """Calculate delay for next retry attempt"""
        if self.config.exponential_backoff:
            delay = self.config.base_delay_seconds * (2 ** self.attempt_count)
        else:
            delay = self.config.base_delay_seconds
        
        # Apply maximum delay limit
        delay = min(delay, self.config.max_delay_seconds)
        
        # Add jitter to prevent thundering herd
        if self.config.jitter:
            jitter_range = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0, delay)  # Ensure non-negative delay


class CircuitBreakerDecorator(BaseAsyncDecorator):
    """Circuit breaker pattern for preventing cascade failures"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_seconds: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        super().__init__("circuit_breaker")
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.expected_exception = expected_exception
        
        # Circuit breaker state
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def _before_execution(self, *args, **kwargs) -> Optional[Any]:
        """Check circuit breaker state before execution"""
        current_time = time.time()
        
        if self.state == "OPEN":
            # Check if timeout period has passed
            if current_time - self.last_failure_time >= self.timeout_seconds:
                self.state = "HALF_OPEN"
            else:
                raise Exception(f"Circuit breaker is OPEN. Service unavailable.")
        
        return None
    
    async def _after_execution(self, result: Any, *args, **kwargs) -> Any:
        """Reset circuit breaker on successful execution"""
        if self.state == "HALF_OPEN":
            # Success in half-open state closes the circuit
            self.state = "CLOSED"
            self.failure_count = 0
        
        return result
    
    async def _on_exception(self, exception: Exception, *args, **kwargs) -> None:
        """Update circuit breaker state on failure"""
        if isinstance(exception, self.expected_exception):
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
            
            if self.state == "HALF_OPEN":
                # Failure in half-open state opens the circuit again
                self.state = "OPEN"
        
        raise exception


class ResilientDecorator(BaseAsyncDecorator):
    """Combined retry + circuit breaker for maximum resilience"""
    
    def __init__(
        self,
        retry_config: RetryConfig = None,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: float = 60.0
    ):
        super().__init__("resilient")
        
        # Initialize retry decorator
        retry_config = retry_config or RetryConfig()
        self.retry_decorator = RetryDecorator(
            max_attempts=retry_config.max_attempts,
            base_delay_seconds=retry_config.base_delay_seconds,
            max_delay_seconds=retry_config.max_delay_seconds,
            exponential_backoff=retry_config.exponential_backoff,
            jitter=retry_config.jitter,
            retryable_exceptions=retry_config.retryable_exceptions
        )
        
        # Initialize circuit breaker
        self.circuit_breaker = CircuitBreakerDecorator(
            failure_threshold=circuit_breaker_threshold,
            timeout_seconds=circuit_breaker_timeout
        )
    
    def decorate(self, func: Callable) -> Callable:
        """Apply both retry and circuit breaker"""
        # First apply circuit breaker, then retry
        decorated_func = self.circuit_breaker.decorate(func)
        decorated_func = self.retry_decorator.decorate(decorated_func)
        return decorated_func
    
    async def _before_execution(self, *args, **kwargs) -> Optional[Any]:
        """Combined pre-execution logic"""
        return None
    
    async def _after_execution(self, result: Any, *args, **kwargs) -> Any:
        """Combined post-execution logic"""
        return result
    
    async def _on_exception(self, exception: Exception, *args, **kwargs) -> None:
        """Combined exception handling"""
        # Exception handling is managed by the composed decorators
        pass