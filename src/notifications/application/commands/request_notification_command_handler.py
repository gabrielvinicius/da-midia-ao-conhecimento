# src/notifications/application/commands/request_notification_command_handler.py
import structlog

from src.auth.application.queries.auth_queries import AuthQueries
from src.shared.events.event_bus import EventBus
from src.shared.events.domain_events import NotificationRequested
from src.notifications.domain.notification import NotificationType
from .request_notification_command import RequestNotificationCommand

logger = structlog.get_logger(__name__)


class RequestNotificationCommandHandler:
    """Handler for the RequestNotificationCommand."""
    def __init__(
        self,
        auth_queries: AuthQueries,
        event_bus: EventBus,
    ):
        self.auth_queries = auth_queries
        self.event_bus = event_bus

    async def handle(self, command: RequestNotificationCommand) -> None:
        """Fetches user contact info and dispatches a NotificationRequested event."""
        logger.info("notification.request_received", user_id=command.user_id, type=command.notification_type)
        
        user = await self.auth_queries.get_by_id(command.user_id)
        if not user:
            raise ValueError("User not found, cannot request notification.")

        contact_info = {
            "email": user.email,
        }

        event = NotificationRequested(
            user_id=command.user_id,
            message=command.message,
            notification_type=command.notification_type,
            contact_info=contact_info
        )
        
        await self.event_bus.publish(event)
        logger.info("notification.request.dispatched", user_id=command.user_id, type=command.notification_type)
