from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# --- Commands ---

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


# --- Queries ---

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

