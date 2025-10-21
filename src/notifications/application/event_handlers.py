# src/notifications/application/event_handlers.py
import logging
from typing import Dict, Any

from src.shared.events.event_bus import EventBus
from src.shared.events.domain_events import NotificationRequested
# FIXED: Application should not import Tasks directly (Infrastructure concern)
from src.shared.application.task_orchestrator import schedule_notification

logger = logging.getLogger(__name__)


async def register_event_handlers(event_bus: EventBus) -> None:
    """Registers all notification-related event handlers."""

    async def handle_notification_requested(event_data: Dict[str, Any]) -> None:
        """Handles NotificationRequested events by triggering the notification sending task."""
        try:
            logger.info(f"Notification requested for user {event_data['user_id']}. Dispatching task.")
            send_notification_task.delay(
                user_id=event_data["user_id"],
                message=event_data["message"],
                notification_type=event_data["notification_type"],
                contact_info=event_data["contact_info"]
            )
        except KeyError as e:
            logger.error(f"Missing required field in NotificationRequested event: {e}")
        except Exception as e:
            logger.error(f"Failed to handle NotificationRequested event: {e}", exc_info=True)

    try:
        event_bus.subscribe(NotificationRequested, handle_notification_requested)
        logger.info("Successfully registered NotificationRequested handler.")
    except Exception as e:
        logger.error(f"Failed to register notification event handlers: {e}", exc_info=True)
        raise
