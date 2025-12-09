from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends

from src.notifications.application.services.notification_service import (
    NotificationService,
)
from src.notifications.infrastructure.adapters.websockets.connection_manager import (
    ConnectionManager,
    manager,
)


class NotificationDependenciesNotConfigured(RuntimeError):
    pass


def get_notification_service() -> NotificationService:
    raise NotificationDependenciesNotConfigured(
        "Notification service is not configured. Register it in the lifespan handler."
    )


def get_connection_manager() -> ConnectionManager:
    """Returns the global instance of the ConnectionManager."""
    return manager


__all__ = [
    "NotificationDependenciesNotConfigured",
    "get_notification_service",
    "get_connection_manager",
]