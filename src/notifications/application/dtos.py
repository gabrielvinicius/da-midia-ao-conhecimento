from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.notifications.domain import NotificationPriority, NotificationType

# --- Commands ---

class SendNotificationCommand(BaseModel):
    model_config = ConfigDict(frozen=True)
    user_id: UUID = Field(
        ...,
        description="ID of the user to send the notification to.",
    )
    message: str = Field(..., description="Content of the notification message.")
    notification_type: NotificationType = Field(
        ..., description="Type of the notification (e.g., EMAIL, SMS, WEBSOCKET)."
    )
    priority: NotificationPriority = Field(
        NotificationPriority.NORMAL, description="Priority of the notification."
    )
    template: Optional[str] = Field(
        None,
        description="Name of the template to use, if any.",
    )
    variables: Optional[Dict[str, Any]] = Field(
        None, description="Variables to render the template, if applicable."
    )



class MarkNotificationAsReadCommand(BaseModel):
    model_config = ConfigDict(frozen=True)
    notification_id: UUID = Field(
        ...,
        description="ID of the notification to mark as read.",
    )
    user_id: UUID = Field(
        ...,
        description="ID of the user who owns the notification.",
    )


class CancelNotificationCommand(BaseModel):
    model_config = ConfigDict(frozen=True)
    notification_id: UUID = Field(..., description="ID of the notification to cancel.")
    user_id: UUID = Field(..., description="ID of the user who owns the notification.")


class CleanupOldNotificationsCommand(BaseModel):
    model_config = ConfigDict(frozen=True)
    days_to_keep: int = Field(
        30,
        ge=0,
        description="Number of days to keep notifications.",
    )

# --- Queries ---

class GetNotificationQuery(BaseModel):
    model_config = ConfigDict(frozen=True)
    notification_id: UUID = Field(
        ...,
        description="ID of the notification to retrieve.",
    )


class GetUserNotificationsQuery(BaseModel):
    model_config = ConfigDict(frozen=True)
    user_id: UUID = Field(
        ...,
        description="ID of the user to retrieve notifications for.",
    )
    include_read: bool = Field(
        True,
        description="Whether to include already read notifications.",
    )
    limit: int = Field(
        50,
        ge=1,
        le=100,
        description="Maximum number of notifications to retrieve.",
    )


class GetNotificationStatsQuery(BaseModel):
    model_config = ConfigDict(frozen=True)
    user_id: Optional[UUID] = Field(
        None,
        description=(
            "ID of the user to retrieve statistics for, or None for global stats."
        ),
    )
