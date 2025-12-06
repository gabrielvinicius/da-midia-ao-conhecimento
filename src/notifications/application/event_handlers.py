"""Async handlers that bridge Notification domain events to delivery pipelines."""
from __future__ import annotations

import structlog

from src.notifications.application.schemas import NotificationTaskPayload
from src.notifications.tasks.notification_tasks import send_notification_task
from src.shared.domain.events import NotificationRequested

logger = structlog.get_logger(__name__).bind(component="notifications.event_handlers")


async def handle_notification_requested(event: NotificationRequested) -> None:
    """Enqueue notification delivery when a request event is published."""
    try:
        payload = NotificationTaskPayload(
            user_id=event.user_id,
            message=event.message,
            notification_type=event.notification_type,
            contact_info=event.contact_info,
        )
        send_notification_task.delay(**payload.model_dump())
    except Exception as exc:  # pragma: no cover - Celery misconfiguration shouldn't crash API
        logger.warning(
            "notification_requested.enqueue_failed",
            user_id=event.user_id,
            error=str(exc),
        )


__all__ = ["handle_notification_requested"]
