"""Montagem dos serviços de notificação: um único lugar para a API e os workers.

O que muda entre os processos é só o canal de entrega: na API, o WebSocket
do navegador; nos workers, o Redis, que a API repassa ao navegador.
"""
from __future__ import annotations

from typing import Optional

from src.notifications.application.ports import AuthQueriesPort, NotificationDeliveryPort
from src.notifications.application.services.notification_read_service import (
    NotificationReadService,
)
from src.notifications.application.services.notification_service import NotificationService
from src.notifications.application.services.pipeline_notification_service import (
    PipelineNotificationService,
)
from src.notifications.infrastructure.adapters.auth_queries_adapter import (
    NotificationsAuthQueriesAdapter,
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


def build_notification_service(
    session,
    *,
    delivery: NotificationDeliveryPort,
    auth_queries: Optional[AuthQueriesPort] = None,
) -> NotificationService:
    repo = NotificationRepositoryAdapter(NotificationRepository(db=session))
    return NotificationService(
        notification_repo=repo,
        delivery=delivery,
        auth_queries=auth_queries or NotificationsAuthQueriesAdapter(db_session=session),
        notification_logger=NotificationLoggerAdapter(),
        notification_metrics=NotificationMetricsAdapter(),
        notification_read_service=NotificationReadService(notification_repo=repo),
    )


def build_pipeline_notification_service(session) -> PipelineNotificationService:
    """Avisos do processamento, enviados pelos workers via Redis."""
    return PipelineNotificationService(
        notification_repo=NotificationRepositoryAdapter(NotificationRepository(db=session)),
        delivery=RedisNotificationDeliveryAdapter(),
        notification_logger=NotificationLoggerAdapter(),
        notification_metrics=NotificationMetricsAdapter(),
    )


__all__ = ["build_notification_service", "build_pipeline_notification_service"]
