# src/notifications/api/routers.py
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from src.notifications.application.dtos import (
    GetNotificationQuery,
    SendNotificationCommand,
)
from src.notifications.domain import NotificationPriority, NotificationType
from src.user_management.api.dependencies import get_current_user
from src.user_management.domain import User, UserRole

from ..application.services.notification_service import NotificationService
from .dependencies import get_notification_service
from .schemas import NotificationRequest, NotificationResponse

# --- Router Definition ---

router = APIRouter(prefix="/notifications", tags=["Notifications"])

# --- Endpoints ---

@router.post("/", status_code=status.HTTP_202_ACCEPTED)
async def request_notification(
    request: NotificationRequest,
    service: NotificationService = Depends(get_notification_service),
    current_user: User = Depends(get_current_user),
):
    if (
        str(request.user_id) != str(current_user.id)
        and current_user.role != UserRole.ADMIN
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to send notification for this user",
        )
    try:
        command = SendNotificationCommand(
            user_id=request.user_id,
            message=request.message,
            notification_type=NotificationType(request.type),
            priority=NotificationPriority.NORMAL,
        )
        notification_id = await service.send_notification(command)
        return {
            "message": "Notification request accepted and is being processed.",
            "notification_id": str(notification_id),
        }
    except ValueError as e:
        # Ideally catch specific domain exceptions
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification_by_id(
    notification_id: UUID, # Changed to UUID, as query expects UUID
    service: NotificationService = Depends(get_notification_service),
    current_user: User = Depends(get_current_user),
):
    query = GetNotificationQuery(notification_id=notification_id)
    notification = await service.get_notification_by_id(query)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    if (
        str(notification.user_id) != str(current_user.id)
        and current_user.role != UserRole.ADMIN
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this notification",
        )

    # Explicit mapping Domain Entity -> DTO
    return NotificationResponse(
        id=notification.id,
        user_id=notification.user_id,
        type=notification.type.value,
        content=notification.content,
        status=notification.status.value,
        priority=notification.priority.value,
        created_at=notification.created_at,
        sent_at=notification.sent_at,
        error_message=notification.error_message
    )
