# src/notifications/api/routers.py
from fastapi import APIRouter, Depends, HTTPException, status

from src.auth.domain.user import User, UserRole
from src.shared.api.dependencies import get_current_user

from .dependencies import get_request_notification_handler, get_notification_queries
from ..application.commands.request_notification_command import RequestNotificationCommand
from ..application.commands.request_notification_command_handler import RequestNotificationCommandHandler
from ..application.queries.notification_queries import NotificationQueries
from .schemas import NotificationResponse, NotificationRequest

# --- Router Definition ---

router = APIRouter(prefix="/notifications", tags=["Notifications"])

# --- Endpoints ---

@router.post("/", status_code=status.HTTP_202_ACCEPTED)
async def request_notification(
    request: NotificationRequest,
    handler: RequestNotificationCommandHandler = Depends(get_request_notification_handler),
    current_user: User = Depends(get_current_user),
):
    if str(request.user_id) != str(current_user.id) and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to send notification for this user")
    try:
        command = RequestNotificationCommand(
            user_id=str(request.user_id), 
            message=request.message, 
            notification_type=request.type
        )
        await handler.handle(command)
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
