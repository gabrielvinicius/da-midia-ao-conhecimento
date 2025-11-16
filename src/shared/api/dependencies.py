# src/shared/api/dependencies.py
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Request, WebSocket, WebSocketException, status
from jose import JWTError, jwt

from src.user_management.api.dependencies import get_auth_queries, get_auth_settings
from src.user_management.application.queries.auth_queries import AuthQueries
from src.user_management.config.settings import AuthSettings
from src.user_management.domain.user import User, UserRole

ACCESS_TOKEN_COOKIE_NAME = "access_token_cookie"


async def get_token_from_cookie(request: Request) -> str:
    """Dependency to extract the token from the access_token_cookie."""
    token = request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


def _extract_bearer_token(header_value: Optional[str]) -> Optional[str]:
    if not header_value:
        return None
    if header_value.lower().startswith("bearer "):
        return header_value.split(" ", 1)[1].strip()
    return None


async def get_token_from_websocket(websocket: WebSocket) -> str:
    """Extract JWT token from websocket cookies, headers or query string."""
    token = websocket.cookies.get(ACCESS_TOKEN_COOKIE_NAME)
    if not token:
        token = _extract_bearer_token(websocket.headers.get("Authorization"))
    if not token:
        token = websocket.query_params.get("token")
    if not token:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Not authenticated",
        )
    return token


async def _resolve_user_from_token(
    token: str,
    settings: AuthSettings,
    queries: AuthQueries,
) -> Optional[User]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None

    return await queries.get_by_id(user_id)


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
    user = await _resolve_user_from_token(token, settings, queries)
    if user is None:
        raise credentials_exception

    return user


async def get_current_user_websocket(
    token: Annotated[str, Depends(get_token_from_websocket)],
    settings: Annotated[AuthSettings, Depends(get_auth_settings)],
    queries: Annotated[AuthQueries, Depends(get_auth_queries)],
) -> User:
    """Dependency to authenticate websocket connections using JWT."""
    user = await _resolve_user_from_token(token, settings, queries)
    if user is None:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Could not validate credentials",
        )
    return user


async def get_current_admin_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Dependency to ensure the current user is an admin."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="The user does not have enough privileges")
    return current_user
