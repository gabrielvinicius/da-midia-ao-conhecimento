# src/user_management/api/dependencies.py
from dataclasses import dataclass
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status, WebSocket, Query
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError

from src.shared.infrastructure.settings import Settings, settings
from src.user_management.application.auth_service import AuthService
from src.user_management.application.queries.dto import GetUserQuery # New import
from src.user_management.application.auth_queries import AuthQueries
from src.user_management.application.user_service import UserService
from src.user_management.domain.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

class AuthDependenciesNotConfigured(RuntimeError):
    """Raised when the dependency provider has not been registered."""


@dataclass(frozen=True)
class AuthDependencies:
    """Aggregates the collaborators required by the auth API."""

    user_service: UserService
    auth_service: AuthService
    auth_queries: AuthQueries
    settings: Settings


def get_auth_dependencies() -> AuthDependencies:
    """Base provider to be overridden during application startup."""
    raise AuthDependenciesNotConfigured(
        "Auth dependencies are not configured. Register providers in the lifespan handler."
    )


AuthDeps = Annotated[AuthDependencies, Depends(get_auth_dependencies)]


def get_user_service(deps: AuthDeps) -> UserService:
    return deps.user_service


def get_auth_service(deps: AuthDeps) -> AuthService:
    return deps.auth_service


def get_auth_queries(deps: AuthDeps) -> AuthQueries:
    return deps.auth_queries


def get_auth_settings(deps: AuthDeps) -> Settings:
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
        payload = jwt.decode(token, deps.settings.secret_key, algorithms=[deps.settings.algorithm])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = await deps.auth_queries.get_user_by_id(GetUserQuery(user_id=user_id))
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
    # Simple check, ideally use same logic
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise HTTPException(status_code=401)
    # Logic similar to get_current_user
    try:
        payload = jwt.decode(token, deps.settings.secret_key, algorithms=[deps.settings.algorithm])
        user_id: str = payload.get("sub")
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise HTTPException(status_code=401)
    
    user = await deps.auth_queries.get_user_by_id(GetUserQuery(user_id=user_id))
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise HTTPException(status_code=401)
    return user

__all__ = [
    "AuthDependencies",
    "AuthDependenciesNotConfigured",
    "get_auth_dependencies",
    "get_auth_queries",
    "get_auth_service",
    "get_auth_settings",
    "get_user_service",
    "get_current_user",
    "get_current_admin_user",
    "get_current_user_websocket",
]