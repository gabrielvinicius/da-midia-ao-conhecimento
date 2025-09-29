# src/notifications/bootstrap.py
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from src.auth.application.queries.auth_queries import AuthQueries
from src.shared.events.event_bus import EventBus
from src.notifications.application.notification_service import NotificationService
from src.notifications.application.queries.notification_queries import NotificationQueries
from src.notifications.infrastructure.notification_repository import NotificationRepository

def bootstrap_notification_module(
    db_session: AsyncSession,
    auth_queries: AuthQueries, # Correct cross-context dependency
    event_bus: EventBus,
) -> Dict[str, Any]:
    """Constructs and returns the services for the notification module."""
    notification_repository = NotificationRepository(db=db_session)
    
    # The service is now a facade for dispatching events
    notification_service = NotificationService(
        auth_queries=auth_queries,
        event_bus=event_bus
    )
    # The query service handles all read operations
    notification_queries = NotificationQueries(notification_repository=notification_repository)

    return {
        "notification_repository": notification_repository,
        "notification_service": notification_service,
        "notification_queries": notification_queries,
    }
