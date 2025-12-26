from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.notifications.application.services.notification_service import (
    NotificationService,
)
from src.notifications.infrastructure.adapters.websockets.connection_manager import (
    ConnectionManager,
    manager,
)
from src.notifications.application.services.notification_read_service import (
    NotificationReadService,
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
from src.notifications.infrastructure.adapters.auth_queries_adapter import (
    NotificationsAuthQueriesAdapter,
)
from src.notifications.infrastructure.repositories.notification_repository import (
    NotificationRepository,
)
from src.shared.infrastructure.database.db import get_db


class NotificationDependenciesNotConfiguredError(RuntimeError):
    """Raised when notification dependencies are missing."""


def get_notification_service(
    session: AsyncSession = Depends(get_db),
) -> NotificationService:
    """Provider padrão (por request) para o serviço de notificações."""

    repo = NotificationRepository(db=session)
    repo_adapter = NotificationRepositoryAdapter(repo)
    read_service = NotificationReadService(notification_repo=repo_adapter)
    auth_queries = NotificationsAuthQueriesAdapter(db_session=session)

    return NotificationService(
        notification_repo=repo_adapter,
        delivery=WebSocketNotificationDeliveryAdapter(),
        auth_queries=auth_queries,
        notification_logger=NotificationLoggerAdapter(),
        notification_metrics=NotificationMetricsAdapter(),
        notification_read_service=read_service,
    )


def get_connection_manager() -> ConnectionManager:
    """Returns the global instance of the ConnectionManager."""
    return manager


__all__ = [
    "NotificationDependenciesNotConfiguredError",
    "get_notification_service",
    "get_connection_manager",
]
