"""
Notifications Commands - Pure data classes following Command Pattern
"""
from dataclasses import dataclass
from typing import Dict, Any

from src.notifications.domain.notification import NotificationType


@dataclass(frozen=True)
class RequestNotificationCommand:
    """Command to request notification"""
    user_id: str
    message: str
    notification_type: NotificationType


@dataclass(frozen=True)
class SendNotificationCommand:
    """Command to send notification"""
    user_id: str
    message: str
    notification_type: NotificationType
    contact_info: Dict[str, Any]