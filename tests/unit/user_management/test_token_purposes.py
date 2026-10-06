"""Cada token só serve para a sua finalidade; o de renovação é revogável."""
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.shared.domain.errors import AuthenticationError
from src.user_management.application.services.auth_service import AuthService
from src.user_management.application.tokens import TokenPurpose
from src.user_management.config.settings import user_settings
from src.user_management.infrastructure.adapters.security.revoked_tokens import InMemoryRevokedTokens
from src.user_management.infrastructure.dependencies.providers import JwtTokenProvider


def _auth(active=True):
    user = SimpleNamespace(id=uuid4(), is_active=active)
    reads = SimpleNamespace(get_user_by_id=AsyncMock(return_value=user))
    users = SimpleNamespace(token_provider=JwtTokenProvider(), user_read_service=reads)
    return AuthService(users, user_settings, revoked_tokens=InMemoryRevokedTokens()), user


@pytest.mark.asyncio
async def test_refresh_token_is_not_an_access_token():
    """Antes, o token de renovação (7 dias) valia como token de acesso."""
    auth, user = _auth()
    tokens = auth.user_service.token_provider
    assert await auth.user_for_token(tokens.create_access_token(user.id)) is user
    with pytest.raises(AuthenticationError):
        await auth.user_for_token(tokens.create_refresh_token(user.id))


@pytest.mark.asyncio
async def test_stream_token_serves_only_its_media_and_not_as_access():
    auth, user = _auth()
    media_id = uuid4()
    issued = auth.issue_scoped_token(user, TokenPurpose.MEDIA_STREAM, media_id)
    assert issued["expires_in"] == user_settings.stream_token_expire_minutes * 60

    assert await auth.user_for_token(issued["token"], TokenPurpose.MEDIA_STREAM, media_id) is user
    for purpose, resource in ((TokenPurpose.MEDIA_STREAM, uuid4()), (TokenPurpose.ACCESS, None), (TokenPurpose.NOTIFICATIONS, None)):
        with pytest.raises(AuthenticationError):
            await auth.user_for_token(issued["token"], purpose, resource)
    # E o de acesso não abre o vídeo: ele não vai mais na URL.
    with pytest.raises(AuthenticationError):
        await auth.user_for_token(auth.user_service.token_provider.create_access_token(user.id), TokenPurpose.MEDIA_STREAM, media_id)


@pytest.mark.asyncio
async def test_inactive_users_and_bad_tokens_are_refused():
    auth, user = _auth(active=False)
    with pytest.raises(AuthenticationError):
        await auth.user_for_token(auth.user_service.token_provider.create_access_token(user.id))
    for bad in (None, "", "lixo"):
        with pytest.raises(AuthenticationError):
            await auth.user_for_token(bad)


@pytest.mark.asyncio
async def test_refresh_rotates_and_logout_revokes():
    auth, user = _auth()
    first = auth.user_service.token_provider.create_refresh_token(user.id)

    second = (await auth.refresh(first))["refresh_token"]
    with pytest.raises(AuthenticationError):  # usado uma vez, não serve de novo
        await auth.refresh(first)

    await auth.logout(second)
    with pytest.raises(AuthenticationError):  # antes, valia por mais 7 dias
        await auth.refresh(second)
