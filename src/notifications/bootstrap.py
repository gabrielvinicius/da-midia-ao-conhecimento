from dataclasses import dataclass

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from src.notifications.api.dependencies import get_notification_service
from src.notifications.application.ports import AuthQueriesPort
from src.notifications.application.services.notification_read_service import (
    NotificationReadService,
)
from src.notifications.application.services.notification_service import (
    NotificationService,
)
from src.notifications.infrastructure.adapters.notification_delivery_adapter import (
    WebSocketNotificationDeliveryAdapter,
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


async def build_notifications_module(
    session: AsyncSession,
    auth_queries: AuthQueriesPort,
    event_bus=None,
) -> NotificationsModule:
    repo = NotificationRepository(db=session)
    repo_adapter = NotificationRepositoryAdapter(repo)
    read_service = NotificationReadService(notification_repo=repo_adapter)

    service = NotificationService(
        notification_repo=repo_adapter,
        delivery=WebSocketNotificationDeliveryAdapter(),
        auth_queries=auth_queries,
        notification_logger=NotificationLoggerAdapter(),
        notification_metrics=NotificationMetricsAdapter(),
        notification_read_service=read_service,
    )
    return NotificationsModule(service=service)


def bind_notifications_module(app: FastAPI, module: NotificationsModule) -> None:
    app.dependency_overrides[get_notification_service] = lambda: module.service


__all__ = [
    "NotificationsModule",
    "build_notifications_module",
    "bind_notifications_module",
]
