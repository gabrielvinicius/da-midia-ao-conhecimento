"""Montagem dos serviços de notificação: um único lugar para a API e os workers.

Os workers criam e entregam os avisos (pelo Redis, que a API repassa ao
navegador); a API lista os avisos e os marca como lidos.
"""
from __future__ import annotations

from src.notifications.application.services.notification_service import NotificationService
from src.notifications.application.services.pipeline_notification_service import (
    PipelineNotificationService,
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
from src.notifications.infrastructure.adapters.redis_notification_delivery_adapter import (
    RedisNotificationDeliveryAdapter,
)
from src.notifications.infrastructure.repositories.notification_repository import (
    NotificationRepository,
)


def build_notification_service(session) -> NotificationService:
    return NotificationService(NotificationRepositoryAdapter(NotificationRepository(db=session)))


def build_pipeline_notification_service(session) -> PipelineNotificationService:
    """Avisos do processamento, enviados pelos workers via Redis."""
    return PipelineNotificationService(
        notification_repo=NotificationRepositoryAdapter(NotificationRepository(db=session)),
        delivery=RedisNotificationDeliveryAdapter(),
        notification_logger=NotificationLoggerAdapter(),
        notification_metrics=NotificationMetricsAdapter(),
    )


__all__ = ["build_notification_service", "build_pipeline_notification_service"]
