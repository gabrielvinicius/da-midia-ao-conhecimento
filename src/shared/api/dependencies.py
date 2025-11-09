# src/shared/api/dependencies.py
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt

from src.user_management.api.dependencies import get_auth_queries, get_auth_settings
from src.user_management.application.queries.auth_queries import AuthQueries
from src.user_management.config.settings import AuthSettings
from src.user_management.domain.user import User, UserRole
from src.user_management.infrastructure.oauth2_scheme import oauth2_scheme


# --- Core Security Dependencies ---

async def get_token_from_cookie(request: Request) -> str:
    """Dependency to extract the token from the access_token_cookie."""
    token = request.cookies.get("access_token_cookie")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


async def get_current_user(
    token: Annotated[str, Depends(get_token_from_cookie)],
    settings: Annotated[AuthSettings, Depends(get_auth_settings)],
    queries: Annotated[AuthQueries, Depends(get_auth_queries)],
) -> User:
    """Dependency to get the current user from a token."""
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


async def get_current_admin_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Dependency to ensure the current user is an admin."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="The user does not have enough privileges")
    return current_user
