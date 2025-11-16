# src/notifications/bootstrap.py
from dataclasses import dataclass

from dependency_injector import containers, providers
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from src.notifications.api.dependencies import (
    NotificationDependencies,
    get_notification_dependencies,
)
from src.notifications.application.queries.notification_queries import (
    NotificationQueries,
)

# Consolidated Service
from src.notifications.application.services.notification_service import (
    NotificationService,
)
from src.notifications.infrastructure.metrics import PrometheusNotificationMetrics
from src.notifications.infrastructure.logging import StructuredNotificationLogger
from src.notifications.infrastructure.connection_manager import manager as connection_manager_instance
from src.notifications.infrastructure.notification_repository import (
    NotificationRepository,
)
from src.user_management.application.queries.auth_queries import AuthQueries


class NotificationContainer(containers.DeclarativeContainer):
    db: providers.Provider[AsyncSession] = providers.Dependency()
    auth_queries: providers.Provider[AuthQueries] = providers.Dependency()

    # Infrastructure Services
    notification_repository = providers.Factory(NotificationRepository, db=db)
    connection_manager = providers.Object(connection_manager_instance)
    notification_logger = providers.Singleton(StructuredNotificationLogger)
    notification_metrics = providers.Singleton(PrometheusNotificationMetrics)

    # Consolidated Application Service
    notification_service = providers.Factory(
        NotificationService,
        notification_repo=notification_repository,
        connection_manager=connection_manager,
        auth_queries=auth_queries,
        # event_bus is no longer used
        notification_logger=notification_logger,
        notification_metrics=notification_metrics,
        email_sender=providers.Object(None),  # Placeholder
        sms_sender=providers.Object(None),   # Placeholder
        push_sender=providers.Object(None)   # Placeholder
    )


@dataclass
class NotificationModule:
    service: NotificationService
    repository: NotificationRepository
    queries: NotificationQueries


async def build_notification_module(
    session: AsyncSession,
    auth_queries: AuthQueries,
) -> NotificationModule:
    container = NotificationContainer(db=session)
    container.auth_queries.override(providers.Object(auth_queries))
    # No event bus needed

    repository = container.notification_repository()
    module = NotificationModule(
        service=container.notification_service(),
        repository=repository,
        queries=NotificationQueries(notification_repository=repository),
    )
    # EventBus handlers disabled; use task-based notifications where needed
    return module


def bind_notification_module(app: FastAPI, module: NotificationModule) -> None:
    """Expose notification services to FastAPI dependency injection."""

    app.dependency_overrides[get_notification_dependencies] = (
        lambda: NotificationDependencies(
            service=module.service,
            queries=module.queries,
        )
    )


__all__ = [
    "NotificationModule",
    "bind_notification_module",
    "build_notification_module",
]
