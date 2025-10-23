# src/notifications/bootstrap.py
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

class NotificationContainer(containers.DeclarativeContainer):
    db: providers.Provider[AsyncSession] = providers.Dependency()
    auth_queries: providers.Provider[AuthQueries] = providers.Dependency()
    event_bus: providers.Provider[EventBus] = providers.Dependency()

    # Infrastructure Services
    notification_repository = providers.Factory(NotificationRepository, db=db)
    connection_manager = providers.Singleton(ConnectionManager, registry=providers.Singleton(lambda: ConnectionManager.registry_instance), logger=providers.Singleton(lambda: ConnectionManager.logger_instance))
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
        email_sender=providers.Object(None), # Placeholder
        sms_sender=providers.Object(None),   # Placeholder
        push_sender=providers.Object(None)   # Placeholder
    )