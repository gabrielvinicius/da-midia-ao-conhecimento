from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.user_management.application.services.auth_service import AuthService


@pytest.mark.asyncio
async def test_authenticate_user_calls_user_service():
    user_service = AsyncMock()
    user_service.authenticate_user.return_value = {"access_token": "test_token"}
    auth_service = AuthService(user_service=user_service, settings={})

    result = await auth_service.authenticate_user("test@example.com", "password")

    user_service.authenticate_user.assert_awaited_once_with("test@example.com", "password")
    assert result == {"access_token": "test_token"}
