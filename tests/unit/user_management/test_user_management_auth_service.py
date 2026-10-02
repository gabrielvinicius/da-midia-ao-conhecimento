from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.user_management.application.services.auth_service import AuthService
from src.user_management.domain.errors import InvalidCredentialsError


def _auth(user=None, payload=None):
    tokens = MagicMock()
    tokens.verify_refresh_token.return_value = payload
    tokens.create_access_token.return_value = "novo-acesso"
    tokens.create_refresh_token.return_value = "nova-renovacao"
    user_service = MagicMock()
    user_service.token_provider = tokens
    user_service.user_read_service.get_user_by_id = AsyncMock(return_value=user)
    user_service.authenticate_user = AsyncMock(return_value={"access_token": "t"})
    return AuthService(user_service=user_service, settings={}), user_service


@pytest.mark.asyncio
async def test_authenticate_user_calls_user_service():
    auth, user_service = _auth()
    assert await auth.authenticate_user("a@b.com", "senha") == {"access_token": "t"}
    user_service.authenticate_user.assert_awaited_once_with("a@b.com", "senha")


@pytest.mark.asyncio
async def test_refresh_issues_new_tokens_for_an_active_user():
    user = SimpleNamespace(id=uuid4(), is_active=True)
    auth, _ = _auth(user, {"sub": str(user.id)})
    assert await auth.refresh("cookie") == {
        "access_token": "novo-acesso",
        "refresh_token": "nova-renovacao",
    }


@pytest.mark.parametrize(
    "user, payload",
    [
        (SimpleNamespace(id=uuid4(), is_active=False), {"sub": "x"}),  # desativado
        (None, {"sub": "x"}),  # excluído
        (None, None),  # token inválido ou expirado
    ],
)
@pytest.mark.asyncio
async def test_refresh_is_refused_without_an_active_user(user, payload):
    auth, user_service = _auth(user, payload)
    with pytest.raises(InvalidCredentialsError):
        await auth.refresh("cookie")
    user_service.token_provider.create_access_token.assert_not_called()
