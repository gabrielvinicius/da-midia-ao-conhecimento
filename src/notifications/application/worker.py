from __future__ import annotations

import structlog
from src.shared.domain.events import (
    SentimentAnalysisCompleted,
    SummarizationCompleted,
    TopicModelingCompleted,
    NotificationRequested,
)
from src.shared.infrastructure.database.db import AsyncSessionLocal
from src.shared.infrastructure.messaging.event_bus_factory import get_event_bus
from src.notifications.bootstrap import bootstrap_task_service
from src.notifications.application.event_handlers import NotificationEventHandlers

logger = structlog.get_logger(__name__)

class NotificationWorkerApp:
    """Worker application logic for Notifications.
    
    Subscribes to analysis completion events to trigger notifications.
    """

    def __init__(self, event_bus=None):
        self.event_bus = event_bus or get_event_bus()
        self._subscribers_bound = False

    def ensure_subscribers(self):
        """Idempotently registers event subscribers for the worker process."""
        if self._subscribers_bound:
            return
        
        self.event_bus.subscribe(SummarizationCompleted, self._on_summarization_completed)
        self.event_bus.subscribe(SentimentAnalysisCompleted, self._on_sentiment_completed)
        self.event_bus.subscribe(TopicModelingCompleted, self._on_topic_modeling_completed)
        self.event_bus.subscribe(NotificationRequested, self._on_notification_requested)
        
        self._subscribers_bound = True
        logger.info("notifications.worker.subscribers_bound")

    async def _on_summarization_completed(self, event: SummarizationCompleted) -> None:
        async with AsyncSessionLocal() as session:
            handlers = self._build_handlers(session)
            await handlers.handle_summarization_completed(event)

    async def _on_sentiment_completed(self, event: SentimentAnalysisCompleted) -> None:
        async with AsyncSessionLocal() as session:
            handlers = self._build_handlers(session)
            await handlers.handle_sentiment_completed(event)

    async def _on_topic_modeling_completed(self, event: TopicModelingCompleted) -> None:
        async with AsyncSessionLocal() as session:
            handlers = self._build_handlers(session)
            await handlers.handle_topic_modeling_completed(event)

    async def _on_notification_requested(self, event: NotificationRequested) -> None:
        async with AsyncSessionLocal() as session:
            handlers = self._build_handlers(session)
            await handlers.handle_notification_requested(event)

    def _build_handlers(self, session):
        service = bootstrap_task_service(session)
        return NotificationEventHandlers(
            event_bus=self.event_bus,
            notification_service=service
        )
