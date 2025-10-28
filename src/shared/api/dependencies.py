# src/shared/api/dependencies.py
from typing import Annotated

from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt

# This file only imports from the domain layer of auth, which is acceptable
# as it defines the core User object contract.
from src.auth.domain.user import User, UserRole
# This is acceptable as it's auth infrastructure used by shared API
from src.auth.infrastructure.oauth2_scheme import oauth2_scheme
from src.auth.api.dependencies import get_auth_queries, get_auth_settings
from src.auth.application.queries.auth_queries import AuthQueries
from src.auth.config.settings import AuthSettings

# --- Core Security Dependencies ---

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

async def get_current_admin_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Dependency to ensure the current user is an admin."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="The user does not have enough privileges")
    return current_user
