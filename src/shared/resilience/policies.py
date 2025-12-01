import logging
import structlog
from typing import Callable, Type

from tenacity import (
    AsyncRetrying,
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log
)

logger = structlog.get_logger("resilience")

def create_retry_policy(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """
    Creates a standard retry decorator with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts before giving up.
        min_wait: Minimum wait time between retries in seconds.
        max_wait: Maximum wait time between retries in seconds.
        exceptions: Tuple of exception types to retry on.
    """
    return retry(
        retry=retry_if_exception_type(exceptions),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=min_wait, min=min_wait, max=max_wait),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )

async def execute_with_retry(
    func: Callable,
    *args,
    max_attempts: int = 3,
    **kwargs
):
    """
    Helper to execute an async function with retry logic dynamically.
    """
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True
    ):
        with attempt:
            return await func(*args, **kwargs)
