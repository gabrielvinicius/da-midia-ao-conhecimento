"""Compatibility command objects preserved for legacy workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from src.notifications.domain.notification import NotificationPriority, NotificationType


@dataclass(slots=True)
class RequestNotificationCommand:
    """Command issued to request that a notification be scheduled."""

    user_id: str
    message: str
    notification_type: NotificationType
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class SendNotificationCommand:
    """Command issued to send a notification immediately."""

    user_id: str
    message: str
    notification_type: NotificationType
    subject: Optional[str] = None
    priority: NotificationPriority = NotificationPriority.NORMAL


__all__ = ["RequestNotificationCommand", "SendNotificationCommand"]
