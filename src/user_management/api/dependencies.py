from dataclasses import dataclass
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Query, WebSocket, WebSocketException, status
from jose import JWTError, ExpiredSignatureError, jwt

from src.user_management.application.auth_queries import UserReadService
from src.user_management.application.dtos import GetUserQuery  # New import
from src.user_management.application.services.auth_service import AuthService
from src.user_management.application.services.user_service import UserService
from src.user_management.config.settings import UserSettings, user_settings
from src.user_management.domain import User, UserRole
from src.user_management.infrastructure.adapters.auth.oauth2_scheme import oauth2_scheme
from src.user_management.infrastructure.adapters.user_repository_adapter import (
    UserRepositoryAdapter,
)
from src.user_management.infrastructure.dependencies.providers import (
    get_password_hasher,
    get_token_provider,
)
from src.user_management.infrastructure.repositories.sqlalchemy_user_repository import (
    UserRepository,
)
from src.shared.infrastructure.database.db import get_db
from sqlalchemy.ext.asyncio import AsyncSession


class AuthDependenciesNotConfiguredError(RuntimeError):
    """Raised when the dependency provider has not been registered."""


@dataclass(frozen=True)
class AuthDependencies:
    """Aggregates the collaborators required by the auth API."""

    user_service: UserService
    auth_service: AuthService
    auth_queries: UserReadService
    settings: UserSettings


def get_auth_dependencies(
    session: AsyncSession = Depends(get_db),
) -> AuthDependencies:
    """Provider padrão (por request) para dependências de autenticação.

    Motivação: evitar session global/singleton (AsyncSession não é thread-safe e
    não deve ser compartilhada entre requests).
    """

    user_repo = UserRepository(db=session)
    user_repo_adapter = UserRepositoryAdapter(user_repo)
    auth_queries = UserReadService(user_repository=user_repo_adapter)

    user_service = UserService(
        user_repository=user_repo_adapter,
        user_read_service=auth_queries,
        password_hasher=get_password_hasher(),
        token_provider=get_token_provider(),
        settings=user_settings,
    )
    auth_service = AuthService(user_service=user_service, settings=user_settings)

    return AuthDependencies(
        user_service=user_service,
        auth_service=auth_service,
        auth_queries=auth_queries,
        settings=user_settings,
    )


AuthDeps = Annotated[AuthDependencies, Depends(get_auth_dependencies)]


def get_user_service(deps: AuthDeps) -> UserService:
    return deps.user_service


def get_auth_service(deps: AuthDeps) -> AuthService:
    return deps.auth_service


def get_auth_queries(deps: AuthDeps) -> UserReadService:
    return deps.auth_queries


def get_auth_settings(deps: AuthDeps) -> UserSettings:
    return deps.settings

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    deps: AuthDeps,
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            deps.settings.secret_key,
            algorithms=[deps.settings.algorithm],
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await deps.auth_queries.get_user_by_id(GetUserQuery(user_id=user_id).user_id)
    if user is None:
        raise credentials_exception
    return user

async def get_current_admin_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have enough privileges",
        )
    return current_user

async def get_current_user_websocket(
    websocket: WebSocket,
    deps: AuthDeps,
    token: Annotated[Optional[str], Query()] = None,
) -> User:
    if not token:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Token ausente")

    try:
        payload = jwt.decode(
            token,
            deps.settings.secret_key,
            algorithms=[deps.settings.algorithm],
        )
        user_id: str = payload.get("sub")
    except ExpiredSignatureError:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Token expirado")
    except JWTError:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Token inválido")

    user = await deps.auth_queries.get_user_by_id(GetUserQuery(user_id=user_id).user_id)
    if not user:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Usuário não encontrado")
    return user

__all__ = [
    "AuthDependencies",
    "AuthDependenciesNotConfiguredError",
    "get_auth_dependencies",
    "get_auth_queries",
    "get_auth_service",
    "get_auth_settings",
    "get_user_service",
    "get_current_user",
    "get_current_admin_user",
    "get_current_user_websocket",
]
