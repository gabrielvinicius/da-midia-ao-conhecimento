# src/notifications/application/commands/send_notification_command_handler.py
import json
import structlog
from typing import Dict, Any

from src.notifications.domain.notification import Notification, NotificationType
from src.notifications.infrastructure.notification_repository import NotificationRepository
from src.notifications.infrastructure.connection_manager import ConnectionManager
from src.shared.utils.id_generator import generate_id
from .send_notification_command import SendNotificationCommand

logger = structlog.get_logger(__name__)


class SendNotificationCommandHandler:
    def __init__(
        self,
        adapter_map: Dict[NotificationType, Any],  # Strategy Pattern: Map of adapters
        notification_repository: NotificationRepository,
        connection_manager: ConnectionManager,  # Added dependency
    ):
        self.adapter_map = adapter_map
        self.notification_repo = notification_repository
        self.connection_manager = connection_manager

    async def handle(self, command: SendNotificationCommand) -> Notification:
        """Handles the notification sending process and pushes a real-time update."""
        notification = Notification(
            id=generate_id(),
            user_id=command.user_id,
            type=command.notification_type,
            content=command.message
        )

        try:
            # This part handles sending via external channels like email, sms, etc.
            adapter = self.adapter_map.get(command.notification_type)
            if not adapter:
                raise ValueError(f"No adapter configured for notification type: {command.notification_type}")

            contact_info = command.contact_info.get(command.notification_type.value.lower())
            if not contact_info:
                raise ValueError(f"Contact info for {command.notification_type} not provided.")

            await adapter.send(contact_info, "Notification", command.message)
            
            notification.mark_as_sent()
            logger.info("notification.sent", notification_id=str(notification.id), type=command.notification_type)
        except Exception as e:
            notification.mark_as_failed(str(e))
            logger.error("notification.failed", notification_id=str(notification.id), error=str(e))

        # Persist the final state of the notification
        saved_notification = await self.notification_repo.save(notification)

        # --- Real-time Notification Push ---
        # After saving, send the notification to the user via WebSocket if they are connected.
        try:
            # Serialize the notification object to a JSON string
            notification_json = saved_notification.model_dump_json()
            await self.connection_manager.send_personal_message(
                message=notification_json,
                user_id=str(saved_notification.user_id)
            )
            logger.info("notification.pushed_realtime", notification_id=str(saved_notification.id), user_id=str(saved_notification.user_id))
        except Exception as e:
            # Log if the real-time push fails, but don't let it fail the whole operation.
            logger.error("notification.realtime_push_failed", notification_id=str(saved_notification.id), error=str(e))

        return saved_notification
