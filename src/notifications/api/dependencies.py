from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends

from src.notifications.application.queries.notification_queries import (
    NotificationQueries,
)
from src.notifications.application.services.notification_service import (
    NotificationService,
)
from src.notifications.infrastructure.connection_manager import (
    ConnectionManager,
    manager,
)


class NotificationDependenciesNotConfigured(RuntimeError):
    pass


@dataclass(frozen=True)
class NotificationDependencies:
    service: NotificationService
    queries: NotificationQueries


def get_notification_dependencies() -> NotificationDependencies:
    raise NotificationDependenciesNotConfigured(
        "Notification dependencies are not configured. Register providers in the lifespan handler."
    )


NotificationDeps = Annotated[
    NotificationDependencies, Depends(get_notification_dependencies)
]


def get_notification_service(deps: NotificationDeps) -> NotificationService:
    return deps.service


def get_notification_queries(deps: NotificationDeps) -> NotificationQueries:
    return deps.queries


def get_connection_manager() -> ConnectionManager:
    """Returns the global instance of the ConnectionManager."""
    return manager


__all__ = [
    "NotificationDependencies",
    "NotificationDependenciesNotConfigured",
    "get_notification_dependencies",
    "get_notification_queries",
    "get_notification_service",
    "get_connection_manager",
]
