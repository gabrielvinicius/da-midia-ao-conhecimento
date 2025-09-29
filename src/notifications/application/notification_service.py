# src/notifications/application/notification_service.py
import structlog

from src.auth.application.queries.auth_queries import AuthQueries
from src.shared.events.event_bus import EventBus
from src.shared.events.domain_events import NotificationRequested
from src.notifications.domain.notification import NotificationType

logger = structlog.get_logger(__name__)


class NotificationService:
    """Facade service to request notifications. It enriches the request with contact info before publishing an event."""
    def __init__(
        self,
        auth_queries: AuthQueries,
        event_bus: EventBus,
    ):
        self.auth_queries = auth_queries
        self.event_bus = event_bus

    async def request_notification(
        self, 
        user_id: str, 
        message: str, 
        notification_type: NotificationType
    ) -> None:
        """Fetches user contact info and dispatches a NotificationRequested event."""
        logger.info("notification.request_received", user_id=user_id, type=notification_type)
        
        user = await self.auth_queries.get_by_id(user_id)
        if not user:
            # In a real system, you might publish a failure event or just log.
            # For now, we raise an error to be handled by the API layer.
            raise ValueError("User not found, cannot request notification.")

        # Enrich the event with the necessary contact info
        contact_info = {
            "email": user.email,
            # "phone": user.phone, # Add when available
            # "webhook_url": user.webhook_url, # Add when available
        }

        event = NotificationRequested(
            user_id=user_id,
            message=message,
            notification_type=notification_type,
            contact_info=contact_info
        )
        
        await self.event_bus.publish(event)
        logger.info("notification.request.dispatched", user_id=user_id, type=notification_type)
