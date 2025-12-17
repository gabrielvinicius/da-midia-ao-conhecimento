from unittest.mock import AsyncMock

import pytest

from src.shared.infrastructure.resilience.retry_policy import create_retry_policy


@pytest.mark.asyncio
async def test_create_retry_policy_success():
    mock_func = AsyncMock(return_value="success")

    @create_retry_policy(max_attempts=3, min_wait=0.01, max_wait=0.1)
    async def decorated_func():
        return await mock_func()

    result = await decorated_func()
    assert result == "success"
    assert mock_func.call_count == 1

@pytest.mark.asyncio
async def test_create_retry_policy_retries_on_exception():
    mock_func = AsyncMock(side_effect=[ValueError("Fail 1"), ValueError("Fail 2"), "success"])

    @create_retry_policy(max_attempts=3, min_wait=0.01, max_wait=0.1, exceptions=(ValueError,))
    async def decorated_func():
        return await mock_func()

    result = await decorated_func()
    assert result == "success"
    assert mock_func.call_count == 3

@pytest.mark.asyncio
async def test_create_retry_policy_fails_after_max_attempts():
    mock_func = AsyncMock(side_effect=ValueError("Fail forever"))

    @create_retry_policy(max_attempts=2, min_wait=0.01, max_wait=0.1, exceptions=(ValueError,))
    async def decorated_func():
        return await mock_func()

    with pytest.raises(ValueError):
        await decorated_func()

    assert mock_func.call_count == 2
