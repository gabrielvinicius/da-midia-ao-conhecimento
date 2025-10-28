# src/notifications/bootstrap.py
from dataclasses import dataclass
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession

# Concrete Implementations
from src.notifications.infrastructure.notification_repository import NotificationRepository
from src.notifications.infrastructure.connection_manager import ConnectionManager
from src.notifications.infrastructure.logging import StructuredNotificationLogger
from src.notifications.infrastructure.metrics import PrometheusNotificationMetrics

# External Dependencies
from src.auth.application.queries.auth_queries import AuthQueries
from src.shared.events.event_bus import EventBus

# Consolidated Service
from src.notifications.application.services.notification_service import NotificationService
from src.notifications.application.queries.notification_queries import NotificationQueries
from src.notifications.application.event_handlers import (
    register_event_handlers as register_notification_handlers,
)


class NotificationContainer(containers.DeclarativeContainer):
    db: providers.Provider[AsyncSession] = providers.Dependency()
    auth_queries: providers.Provider[AuthQueries] = providers.Dependency()
    event_bus: providers.Provider[EventBus] = providers.Dependency()

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
        event_bus=event_bus,
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
    event_bus: EventBus,
) -> NotificationModule:
    container = NotificationContainer(db=session)
    container.auth_queries.override(providers.Object(auth_queries))
    container.event_bus.override(providers.Object(event_bus))

    repository = container.notification_repository()
    module = NotificationModule(
        service=container.notification_service(),
        repository=repository,
        queries=NotificationQueries(notification_repository=repository),
    )
    await register_notification_handlers(event_bus)
    return module
