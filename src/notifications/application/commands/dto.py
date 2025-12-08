from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
from uuid import UUID

from src.notifications.domain.notification import (
    NotificationPriority,
    NotificationType,
)


class SendNotificationCommand(BaseModel):
    user_id: UUID = Field(..., description="ID of the user to send the notification to.")
    message: str = Field(..., description="Content of the notification message.")
    notification_type: NotificationType = Field(
        ..., description="Type of the notification (e.g., EMAIL, SMS, WEBSOCKET)."
    )
    priority: NotificationPriority = Field(
        NotificationPriority.NORMAL, description="Priority of the notification."
    )
    template: Optional[str] = Field(None, description="Name of the template to use, if any.")
    variables: Optional[Dict[str, Any]] = Field(
        None, description="Variables to render the template, if applicable."
    )

    class Config:
        frozen = True


class MarkNotificationAsReadCommand(BaseModel):
    notification_id: UUID = Field(..., description="ID of the notification to mark as read.")
    user_id: UUID = Field(..., description="ID of the user who owns the notification.")

    class Config:
        frozen = True


class CancelNotificationCommand(BaseModel):
    notification_id: UUID = Field(..., description="ID of the notification to cancel.")
    user_id: UUID = Field(..., description="ID of the user who owns the notification.")

    class Config:
        frozen = True


class CleanupOldNotificationsCommand(BaseModel):
    days_to_keep: int = Field(30, ge=0, description="Number of days to keep notifications.")

    class Config:
        frozen = True
