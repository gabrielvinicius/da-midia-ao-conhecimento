from dataclasses import dataclass
from typing import Optional

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from src.notifications.api.dependencies import get_notification_service
from src.notifications.application.ports import AuthQueriesPort, NotificationDeliveryPort
from src.notifications.application.services.notification_read_service import (
    NotificationReadService,
)
from src.notifications.application.services.notification_service import (
    NotificationService,
)
from src.notifications.application.services.pipeline_notification_service import (
    PipelineNotificationService,
)
from src.notifications.infrastructure.adapters.auth_queries_adapter import (
    NotificationsAuthQueriesAdapter,
)
from src.notifications.infrastructure.adapters.notification_delivery_adapter import (
    WebSocketNotificationDeliveryAdapter,
)
from src.notifications.infrastructure.adapters.redis_notification_delivery_adapter import (
    RedisNotificationDeliveryAdapter,
)
from src.notifications.infrastructure.adapters.notification_logger_adapter import (
    NotificationLoggerAdapter,
)
from src.notifications.infrastructure.adapters.notification_metrics_adapter import (
    NotificationMetricsAdapter,
)
from src.notifications.infrastructure.adapters.notification_repository_adapter import (
    NotificationRepositoryAdapter,
)
from src.notifications.infrastructure.repositories.notification_repository import (
    NotificationRepository,
)


@dataclass
class NotificationsModule:
    service: NotificationService


def build_notifications_module(
    session: AsyncSession,
    auth_queries: AuthQueriesPort,
    event_bus=None,
    delivery_adapter: Optional[NotificationDeliveryPort] = None,
) -> NotificationsModule:
    """Builds the notifications module with dependencies."""
    repo = NotificationRepository(db=session)
    repo_adapter = NotificationRepositoryAdapter(repo)
    read_service = NotificationReadService(notification_repo=repo_adapter)

    # Default to WebSocket delivery if not provided (for API context)
    delivery = delivery_adapter or WebSocketNotificationDeliveryAdapter()

    service = NotificationService(
        notification_repo=repo_adapter,
        delivery=delivery,
        auth_queries=auth_queries,
        notification_logger=NotificationLoggerAdapter(),
        notification_metrics=NotificationMetricsAdapter(),
        notification_read_service=read_service,
    )
    return NotificationsModule(service=service)


def bootstrap_task_service(session) -> NotificationService:
    """Helper to bootstrap the service for Celery tasks (Sync/Async bridge).
    
    Uses Redis delivery by default since tasks run in worker context.
    """
    repo = NotificationRepository(db=session)
    repo_adapter = NotificationRepositoryAdapter(repo)
    read_service = NotificationReadService(notification_repo=repo_adapter)
    
    # Tasks running in worker must use Redis to bridge back to API
    delivery = RedisNotificationDeliveryAdapter()
    
    # Worker needs direct DB queries for auth
    auth_queries = NotificationsAuthQueriesAdapter(db_session=session)

    return NotificationService(
        notification_repo=repo_adapter,
        delivery=delivery,
        auth_queries=auth_queries,
        notification_logger=NotificationLoggerAdapter(),
        notification_metrics=NotificationMetricsAdapter(),
        notification_read_service=read_service,
    )


def bootstrap_pipeline_notification_service(session) -> PipelineNotificationService:
    """Helper to bootstrap the lightweight pipeline notification service.
    
    Used by media_processing tasks to send status updates.
    """
    repo = NotificationRepository(db=session)
    # Tasks running in worker must use Redis to bridge back to API
    delivery = RedisNotificationDeliveryAdapter()
    
    return PipelineNotificationService(
        notification_repo=NotificationRepositoryAdapter(repo),
        delivery=delivery,
        notification_logger=NotificationLoggerAdapter(),
        notification_metrics=NotificationMetricsAdapter(),
    )


def bind_notifications_module(app: FastAPI, module: NotificationsModule) -> None:
    app.dependency_overrides[get_notification_service] = lambda: module.service


__all__ = [
    "NotificationsModule",
    "build_notifications_module",
    "bootstrap_task_service",
    "bootstrap_pipeline_notification_service",
    "bind_notifications_module",
]
