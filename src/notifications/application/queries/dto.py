from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID


class GetNotificationQuery(BaseModel):
    notification_id: UUID = Field(..., description="ID of the notification to retrieve.")

    class Config:
        frozen = True


class GetUserNotificationsQuery(BaseModel):
    user_id: UUID = Field(..., description="ID of the user to retrieve notifications for.")
    include_read: bool = Field(True, description="Whether to include already read notifications.")
    limit: int = Field(50, ge=1, le=100, description="Maximum number of notifications to retrieve.")

    class Config:
        frozen = True


class GetNotificationStatsQuery(BaseModel):
    user_id: Optional[UUID] = Field(None, description="ID of the user to retrieve statistics for, or None for global stats.")

    class Config:
        frozen = True
