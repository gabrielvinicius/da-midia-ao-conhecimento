"""Dependências da autenticação.

Os serviços são ligados por bootstrap.bind_user_management_module; sem essa
ligação, as dependências falham em vez de montar uma versão própria.
"""
from typing import Annotated, Optional

from uuid import UUID

from fastapi import Depends, Query, WebSocketException, status

from src.user_management.application.auth_queries import UserReadService
from src.shared.application.access import Requester
from src.shared.domain.errors import AccessDeniedError, AuthenticationError
from src.user_management.application.services.auth_service import AuthService
from src.user_management.application.services.login_throttle import LoginThrottle
from src.user_management.application.services.user_service import UserService
from src.user_management.application.tokens import TokenPurpose
from src.user_management.config.settings import UserSettings
from src.user_management.domain import User, UserRole
from src.user_management.infrastructure.adapters.auth.oauth2_scheme import oauth2_scheme


# --- Placeholder Dependencies (Contracts) ---

def get_user_service() -> UserService:
    """Returns the UserService instance."""
    raise NotImplementedError("UserService dependency not configured.")


def get_auth_service() -> AuthService:
    """Returns the AuthService instance."""
    raise NotImplementedError("AuthService dependency not configured.")


def get_auth_queries() -> UserReadService:
    """Returns the UserReadService (CQRS Query side) instance."""
    raise NotImplementedError("AuthQueries dependency not configured.")


def get_auth_settings() -> UserSettings:
    """Returns the UserSettings instance."""
    raise NotImplementedError("AuthSettings dependency not configured.")


_default_login_throttle: Optional[LoginThrottle] = None


def get_login_throttle() -> LoginThrottle:
    """Limitador de tentativas de login.

    A raiz de composição substitui esta dependência por uma instância com Redis
    (compartilhada entre processos). Sem substituição, usa contagem em memória.
    """
    global _default_login_throttle
    if _default_login_throttle is None:
        from src.user_management.config.settings import user_settings
        from src.user_management.infrastructure.adapters.security.login_attempt_limiter import (
            InMemoryLoginAttemptLimiter,
        )

        _default_login_throttle = LoginThrottle(
            InMemoryLoginAttemptLimiter(),
            user_settings.login_max_attempts_per_email,
            user_settings.login_max_attempts_per_ip,
            user_settings.login_block_seconds,
        )
    return _default_login_throttle


# --- Usuário autenticado ---------------------------------------------------
# Toda a verificação fica em AuthService.user_for_token; aqui só se escolhe
# de onde vem o token e para que ele precisa servir.

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    auth: AuthService = Depends(get_auth_service),
) -> User:
    """Usuário do token de acesso (cabeçalho Authorization)."""
    return await auth.user_for_token(token, TokenPurpose.ACCESS)


async def get_requester(current_user: Annotated[User, Depends(get_current_user)]) -> Requester:
    """Quem pede (id e perfil), para as regras de acesso dos serviços."""
    return Requester(current_user.id, current_user.role)


async def get_current_user_for_media_stream(
    media_id: UUID,
    token: Annotated[str, Query(..., description="Token de reprodução (POST /auth/scoped-token).")],
    auth: AuthService = Depends(get_auth_service),
) -> User:
    """Usuário do token de reprodução daquela mídia, na URL do <video>."""
    return await auth.user_for_token(token, TokenPurpose.MEDIA_STREAM, media_id)


async def get_current_admin_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if current_user.role != UserRole.ADMIN:
        raise AccessDeniedError("Acesso restrito a administradores")
    return current_user


async def get_current_user_websocket(
    token: Annotated[Optional[str], Query()] = None,
    auth: AuthService = Depends(get_auth_service),
) -> User:
    """Usuário do token de abertura do WebSocket de avisos."""
    try:
        return await auth.user_for_token(token, TokenPurpose.NOTIFICATIONS)
    except AuthenticationError as exc:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason=str(exc)) from None


__all__ = [
    "get_user_service",
    "get_auth_service",
    "get_auth_queries",
    "get_auth_settings",
    "get_current_user",
    "get_requester",
    "get_current_user_for_media_stream",
    "get_current_admin_user",
    "get_current_user_websocket",
    "get_login_throttle",
]
