# src/notifications/application/commands/send_notification_command_handler.py
import structlog

from src.notifications.domain.notification import Notification, NotificationType
from src.notifications.infrastructure.notification_repository import NotificationRepository
from src.shared.utils.id_generator import generate_id
from .send_notification_command import SendNotificationCommand

logger = structlog.get_logger(__name__)


class SendNotificationCommandHandler:
    def __init__(
        self,
        email_adapter,
        sms_adapter,
        webhook_adapter,
        notification_repository: NotificationRepository,
    ):
        self.email_adapter = email_adapter
        self.sms_adapter = sms_adapter
        self.webhook_adapter = webhook_adapter
        self.notification_repo = notification_repository

    async def handle(self, command: SendNotificationCommand) -> Notification:
        """Handles the notification sending process using data from the command."""
        notification = Notification(
            id=generate_id(),
            user_id=command.user_id,
            type=command.notification_type,
            content=command.message
        )
        await self.notification_repo.save(notification)

        try:
            if command.notification_type == NotificationType.EMAIL:
                email_address = command.contact_info.get("email")
                if not email_address:
                    raise ValueError("Email address not provided in contact_info for EMAIL notification.")
                await self.email_adapter.send(email_address, "Notification", command.message)
            
            # Similar logic for SMS and WEBHOOK would be added here

            notification.mark_as_sent()
            logger.info("notification.sent", notification_id=str(notification.id), type=command.notification_type)
        except Exception as e:
            notification.mark_as_failed(str(e))
            logger.error("notification.failed", notification_id=str(notification.id), error=str(e))

        await self.notification_repo.save(notification)
        return notification
