# src/auth/api/dependencies.py
from typing import Annotated
from fastapi import Depends, HTTPException, status, Request, Query
from jose import JWTError, jwt

from src.auth.application.auth_service import AuthService
from src.auth.application.queries.auth_queries import AuthQueries
from src.auth.config.settings import AuthSettings
from src.auth.domain.user import User, UserRole
from src.auth.infrastructure.oauth2_scheme import oauth2_scheme

# --- Settings and Service Getters ---

def get_container(request: Request) -> dict:
    return request.app.state.container

def get_auth_settings(container: Annotated[dict, Depends(get_container)]) -> AuthSettings:
    return container["auth_settings"]

def get_auth_service(container: Annotated[dict, Depends(get_container)]) -> AuthService:
    return container["auth_service"]

def get_auth_queries(container: Annotated[dict, Depends(get_container)]) -> AuthQueries:
    return container["auth_queries"]

# --- User Dependency Functions ---

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    settings: Annotated[AuthSettings, Depends(get_auth_settings)],
    queries: Annotated[AuthQueries, Depends(get_auth_queries)],
) -> User:
    """Dependency to get the current user from an OAuth2 token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await queries.get_by_id(user_id)
    if user is None:
        raise credentials_exception
    return user

async def get_current_user_from_token(
    token: Annotated[str, Query(...)],
    settings: Annotated[AuthSettings, Depends(get_auth_settings)],
    queries: Annotated[AuthQueries, Depends(get_auth_queries)],
) -> User:
    """Dependency to get the current user from a token passed as a query parameter (for WebSockets)."""
    # This is the same logic as get_current_user, but adapted for query param token
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await queries.get_by_id(user_id)
    if user is None:
        raise credentials_exception
    return user

async def get_current_admin_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Dependency to ensure the current user is an admin."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="The user does not have enough privileges")
    return current_user
