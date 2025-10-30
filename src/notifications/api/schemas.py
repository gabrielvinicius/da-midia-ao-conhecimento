# src/notifications/api/schemas.py
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from src.notifications.domain.notification import NotificationType


class NotificationRequest(BaseModel):
    user_id: UUID
    message: str
    type: NotificationType


class NotificationResponse(BaseModel):
    id: UUID
    user_id: UUID
    type: str
    content: str
    status: str
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
