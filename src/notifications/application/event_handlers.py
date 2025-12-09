"""Async handlers that bridge Notification domain events to delivery pipelines."""
from __future__ import annotations

import structlog
from typing import Any

from src.notifications.application.commands.dto import SendNotificationCommand
from src.notifications.application.services.notification_service import NotificationService
from src.notifications.domain.notification import NotificationType, NotificationPriority
from src.shared.domain.events import (
    NotificationRequested,
    SummarizationCompleted,
    SentimentAnalysisCompleted,
    TopicModelingCompleted,
)
from src.shared.infrastructure.messaging.event_bus import SupportsEventBus

logger = structlog.get_logger(__name__).bind(component="notifications.event_handlers")


class NotificationEventHandlers:
    def __init__(self, event_bus: SupportsEventBus, notification_service: NotificationService):
        self.event_bus = event_bus
        self.notification_service = notification_service

    async def handle_notification_requested(self, event: NotificationRequested) -> None:
        """Directly handle the notification request by sending it via the service."""
        try:
            # Map event to Command DTO
            # Note: event.notification_type is a string, need to convert to Enum
            try:
                notif_type = NotificationType(event.notification_type)
            except ValueError:
                notif_type = NotificationType.WEBSOCKET # Default?

            command = SendNotificationCommand(
                user_id=event.user_id,
                message=event.message,
                notification_type=notif_type,
                priority=NotificationPriority.NORMAL,
                variables=event.contact_info
            )
            await self.notification_service.send_notification(command)
        except Exception as exc:
            logger.warning(
                "notification_requested.handle_failed",
                user_id=event.user_id,
                error=str(exc),
            )

    async def handle_summarization_completed(self, event: SummarizationCompleted) -> None:
        await self._publish_notification_request(
            user_id=event.user_id,
            media_id=event.media_id,
            message=f"Summarization completed for media {event.media_id}",
            kind="summarization"
        )

    async def handle_sentiment_completed(self, event: SentimentAnalysisCompleted) -> None:
        await self._publish_notification_request(
            user_id=event.user_id,
            media_id=event.media_id,
            message=f"Sentiment analysis completed for media {event.media_id}. Score: {event.sentiment_score}",
            kind="sentiment"
        )

    async def handle_topic_modeling_completed(self, event: TopicModelingCompleted) -> None:
        await self._publish_notification_request(
            user_id=event.user_id,
            media_id=event.media_id,
            message=f"Topic modeling completed for media {event.media_id}",
            kind="topic_modeling"
        )

    async def _publish_notification_request(self, user_id: str | None, media_id: Any, message: str, kind: str) -> None:
        if not user_id:
            # Log warning: cannot notify without user_id
            return
            
        event = NotificationRequested(
            user_id=user_id,
            message=message,
            notification_type="WEBSOCKET", # Default to websocket for now
            contact_info={"media_id": str(media_id), "kind": kind}
        )
        await self.event_bus.publish(event) 

__all__ = ["NotificationEventHandlers"]