# src/notifications/bootstrap.py
from dataclasses import dataclass

from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession
from src.notifications.infrastructure.logging import StructuredNotificationLogger
from src.notifications.infrastructure.metrics import PrometheusNotificationMetrics

# External Dependencies
from src.auth.application.queries.auth_queries import AuthQueries
from src.notifications.application.queries.notification_queries import NotificationQueries
# Consolidated Service
from src.notifications.application.services.notification_service import NotificationService
from src.notifications.infrastructure.connection_manager import ConnectionManager
# Concrete Implementations
from src.notifications.infrastructure.notification_repository import NotificationRepository


class NotificationContainer(containers.DeclarativeContainer):
    db: providers.Provider[AsyncSession] = providers.Dependency()
    auth_queries: providers.Provider[AuthQueries] = providers.Dependency()

    # Infrastructure Services
    notification_repository = providers.Factory(NotificationRepository, db=db)
    connection_manager = providers.Singleton(
        ConnectionManager,
        registry=providers.Singleton(lambda: ConnectionManager.registry_instance),
        logger=providers.Singleton(lambda: ConnectionManager.logger_instance),
    )
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
