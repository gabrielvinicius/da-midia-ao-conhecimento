"""Pydantic schemas for notification task payloads."""
from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel, Field


class NotificationTaskPayload(BaseModel):
    """Validates the data required to send a notification asynchronously."""

    user_id: str = Field(min_length=1)
    message: str = Field(min_length=1)
    notification_type: str = Field(min_length=1)
    contact_info: Dict[str, Any] = Field(default_factory=dict)


__all__ = ["NotificationTaskPayload"]
