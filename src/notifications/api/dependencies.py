

from src.notifications.application.services.notification_service import (
    NotificationService,
)
from src.notifications.infrastructure.adapters.websockets.connection_manager import (
    ConnectionManager,
    manager,
)


class NotificationDependenciesNotConfiguredError(RuntimeError):
    """Raised when notification dependencies are missing."""


def get_notification_service() -> NotificationService:
    raise NotificationDependenciesNotConfiguredError(
        "Notification service is not configured. Register it in the lifespan handler."
    )


def get_connection_manager() -> ConnectionManager:
    """Returns the global instance of the ConnectionManager."""
    return manager


__all__ = [
    "NotificationDependenciesNotConfiguredError",
    "get_notification_service",
    "get_connection_manager",
]
