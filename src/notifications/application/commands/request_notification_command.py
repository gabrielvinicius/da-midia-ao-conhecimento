# src/notifications/application/commands/request_notification_command.py
from dataclasses import dataclass
from src.notifications.domain.notification import NotificationType

@dataclass(frozen=True)
class RequestNotificationCommand:
    """Command to request a new notification."""
    user_id: str
    message: str
    notification_type: NotificationType
