# src/notifications/api/routers.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Annotated, Any
from jose import JWTError, jwt

# --- Local Dependency Injection and Security Logic ---

from src.auth.domain.user import User, UserRole
from src.auth.config.settings import AuthSettings
from src.auth.application.queries.auth_queries import AuthQueries
from src.auth.infrastructure.oauth2_scheme import oauth2_scheme
from .dependencies import get_notification_service, get_notification_queries
from ..application.notification_service import NotificationService
from ..application.queries.notification_queries import NotificationQueries
from .schemas import NotificationResponse, NotificationRequest

def get_container(request: Request) -> dict:
    return request.app.state.container

def get_notification_service(container: Annotated[dict, Depends(get_container)]) -> NotificationService:
    return container["notification_service"]

def get_notification_queries(container: Annotated[dict, Depends(get_container)]) -> NotificationQueries:
    return container["notification_queries"]

def get_auth_queries(container: Annotated[dict, Depends(get_container)]) -> AuthQueries:
    return container["auth_queries"]

def get_auth_settings(container: Annotated[dict, Depends(get_container)]) -> AuthSettings:
    return container["auth_settings"]

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    settings: Annotated[AuthSettings, Depends(get_auth_settings)],
    queries: Annotated[AuthQueries, Depends(get_auth_queries)],
) -> User:
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("sub")
        if user_id is None: raise credentials_exception
    except JWTError: raise credentials_exception
    user = await queries.get_by_id(user_id)
    if user is None: raise credentials_exception
    return user

# --- Router Definition ---

router = APIRouter(prefix="/notifications", tags=["Notifications"])

# --- Endpoints ---

@router.post("/", status_code=status.HTTP_202_ACCEPTED)
async def request_notification(
    request: NotificationRequest,
    service: NotificationService = Depends(get_notification_service),
    current_user: User = Depends(get_current_user),
):
    if str(request.user_id) != str(current_user.id) and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to send notification for this user")
    try:
        await service.request_notification(user_id=str(request.user_id), message=request.message, notification_type=request.type)
        return {"message": "Notification request accepted and is being processed."}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification_by_id(
    notification_id: str, 
    queries: NotificationQueries = Depends(get_notification_queries),
    current_user: User = Depends(get_current_user),
):
    notification = await queries.get_by_id(notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    if str(notification.user_id) != str(current_user.id) and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this notification")
    return notification
