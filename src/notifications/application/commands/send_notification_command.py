# src/notifications/application/commands/send_notification_command.py
from dataclasses import dataclass
from typing import Dict, Any
from src.notifications.domain.notification import NotificationType

@dataclass(frozen=True)
class SendNotificationCommand:
    user_id: str
    message: str
    notification_type: NotificationType
    contact_info: Dict[str, Any]
