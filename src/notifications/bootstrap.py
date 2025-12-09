# src/notifications/bootstrap.py
from dataclasses import dataclass

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from src.notifications.api.dependencies import (
    get_notification_service,
)

# Consolidated Service
from src.notifications.application.services.notification_service import (
    NotificationService,
)
from src.notifications.application.notification_read_service import NotificationReadService
from src.notifications.application.event_handlers import NotificationEventHandlers
from src.notifications.infrastructure.metrics.prometheus_metrics import PrometheusNotificationMetrics
from src.notifications.infrastructure.logging.structured_logger import StructuredNotificationLogger
from src.notifications.infrastructure.adapters.websockets.connection_manager import manager as connection_manager_instance
from src.notifications.infrastructure.repositories.notification_repository import (
    NotificationRepository,
)
from src.shared.infrastructure.messaging.event_bus import SupportsEventBus
from src.shared.domain.events import (
    NotificationRequested,
    SummarizationCompleted,
    SentimentAnalysisCompleted,
    TopicModelingCompleted,
)
from src.user_management.application.auth_queries import AuthQueries


@dataclass
class NotificationModule:
    service: NotificationService
    repository: NotificationRepository


async def build_notification_module(
    session: AsyncSession,
    auth_queries: AuthQueries,
    event_bus: SupportsEventBus | None = None,
) -> NotificationModule:
    repository = NotificationRepository(db=session)
    notification_read_service = NotificationReadService(notification_repo=repository)
    notification_logger = StructuredNotificationLogger()
    notification_metrics = PrometheusNotificationMetrics()
    connection_manager = connection_manager_instance
    service = NotificationService(
        notification_repo=repository,
        connection_manager=connection_manager,
        auth_queries=auth_queries,
        notification_logger=notification_logger,
        notification_metrics=notification_metrics,
        notification_read_service=notification_read_service,
        email_sender=None,
        sms_sender=None,
        push_sender=None,
    )

    if event_bus:
        handlers = NotificationEventHandlers(event_bus=event_bus, notification_service=service)
        event_bus.subscribe(NotificationRequested, handlers.handle_notification_requested)
        event_bus.subscribe(SummarizationCompleted, handlers.handle_summarization_completed)
        event_bus.subscribe(SentimentAnalysisCompleted, handlers.handle_sentiment_completed)
        event_bus.subscribe(TopicModelingCompleted, handlers.handle_topic_modeling_completed)

    module = NotificationModule(
        service=service,
        repository=repository,
    )
    return module


def bind_notification_module(app: FastAPI, module: NotificationModule) -> None:
    """Expose notification services to FastAPI dependency injection."""

    app.dependency_overrides[get_notification_service] = lambda: module.service


__all__ = [
    "NotificationModule",
    "bind_notification_module",
    "build_notification_module",
]