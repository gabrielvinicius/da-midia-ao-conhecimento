# src/notifications/application/commands/send_notification_command_handler.py
import structlog
from typing import Dict, Any

from src.notifications.domain.notification import Notification, NotificationType
from src.notifications.infrastructure.notification_repository import NotificationRepository
from src.shared.utils.id_generator import generate_id
from .send_notification_command import SendNotificationCommand

logger = structlog.get_logger(__name__)


class SendNotificationCommandHandler:
    def __init__(
        self,
        adapter_map: Dict[NotificationType, Any], # Strategy Pattern: Map of adapters
        notification_repository: NotificationRepository,
    ):
        self.adapter_map = adapter_map
        self.notification_repo = notification_repository

    async def handle(self, command: SendNotificationCommand) -> Notification:
        """Handles the notification sending process using a strategy pattern for adapters."""
        notification = Notification(
            id=generate_id(),
            user_id=command.user_id,
            type=command.notification_type,
            content=command.message
        )
        # The entity is now only saved once at the end.

        try:
            adapter = self.adapter_map.get(command.notification_type)
            if not adapter:
                raise ValueError(f"No adapter configured for notification type: {command.notification_type}")

            # Get contact info from the enriched command
            contact_info = command.contact_info.get(command.notification_type.value.lower())
            if not contact_info:
                raise ValueError(f"Contact info for {command.notification_type} not provided.")

            await adapter.send(contact_info, "Notification", command.message)
            
            notification.mark_as_sent()
            logger.info("notification.sent", notification_id=str(notification.id), type=command.notification_type)
        except Exception as e:
            notification.mark_as_failed(str(e))
            logger.error("notification.failed", notification_id=str(notification.id), error=str(e))

        # Persist the final state of the notification once.
        return await self.notification_repo.save(notification)
