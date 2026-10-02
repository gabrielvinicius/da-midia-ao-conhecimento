"""Authentication dependencies contract.

This module defines the dependency interfaces (functions) used by the API routers.
These functions are placeholders that raise NotImplementedError by default.
They MUST be overridden by the application Composition Root (main.py) using
FastAPI's app.dependency_overrides mechanism.
"""
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Query, WebSocketException, status
from jose import JWTError, ExpiredSignatureError, jwt

from src.user_management.application.auth_queries import UserReadService
from src.user_management.application.dtos import GetUserQuery
from src.user_management.application.services.auth_service import AuthService
from src.user_management.application.services.login_throttle import LoginThrottle
from src.user_management.application.services.user_service import UserService
from src.user_management.config.settings import UserSettings
from src.user_management.domain import User, UserRole
from src.user_management.infrastructure.adapters.auth.oauth2_scheme import oauth2_scheme


# --- Placeholder Dependencies (Contracts) ---

def get_auth_dependencies() -> None:
    """Deprecated placeholder. Use specific service getters below."""
    raise NotImplementedError("Legacy dependency. Use specific services.")


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


# --- Derived Dependencies (Leafs) ---

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    queries: UserReadService = Depends(get_auth_queries),
    settings: UserSettings = Depends(get_auth_settings),
) -> User:
    """Resolves the current authenticated user from the Bearer token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await queries.get_user_by_id(GetUserQuery(user_id=user_id).user_id)
    # Conta excluída ou desativada perde o acesso já na próxima requisição,
    # mesmo com um token ainda dentro da validade.
    if user is None or not user.is_active:
        raise credentials_exception
    return user


async def get_current_user_from_query(
    token: Annotated[str, Query(...)],
    queries: UserReadService = Depends(get_auth_queries),
    settings: UserSettings = Depends(get_auth_settings),
) -> User:
    """Resolves current user from a 'token' query parameter (for streaming/ws)."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await queries.get_user_by_id(GetUserQuery(user_id=user_id).user_id)
    # Conta excluída ou desativada perde o acesso já na próxima requisição,
    # mesmo com um token ainda dentro da validade.
    if user is None or not user.is_active:
        raise credentials_exception
    return user


async def get_current_admin_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Ensures the current user has ADMIN privileges."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have enough privileges",
        )
    return current_user


async def get_current_user_websocket(
    token: Annotated[Optional[str], Query()] = None,
    queries: UserReadService = Depends(get_auth_queries),
    settings: UserSettings = Depends(get_auth_settings),
) -> User:
    """Resolves current user for WebSocket connections."""
    if not token:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Token ausente")

    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        user_id: str = payload.get("sub")
    except ExpiredSignatureError:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Token expirado")
    except JWTError:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Token inválido")

    user = await queries.get_user_by_id(GetUserQuery(user_id=user_id).user_id)
    if not user or not user.is_active:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Usuário não encontrado")
    return user


__all__ = [
    "get_user_service",
    "get_auth_service",
    "get_auth_queries",
    "get_auth_settings",
    "get_current_user",
    "get_current_user_from_query",
    "get_current_admin_user",
    "get_current_user_websocket",
]