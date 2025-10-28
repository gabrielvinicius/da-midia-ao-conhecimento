from typing import Annotated
from fastapi import Depends, Request

from src.notifications.application.services.notification_service import NotificationService
from src.notifications.application.queries.notification_queries import NotificationQueries
from src.notifications.infrastructure.connection_manager import ConnectionManager
from src.shared.application.modules import ModulesRegistry
from src.notifications.infrastructure.connection_manager import manager


def get_modules(request: Request) -> ModulesRegistry:
    return request.app.state.modules


def get_notification_service(
    modules: Annotated[ModulesRegistry, Depends(get_modules)]
) -> NotificationService:
    return modules.notifications.service


def get_notification_queries(
    modules: Annotated[ModulesRegistry, Depends(get_modules)]
) -> NotificationQueries:
    return modules.notifications.queries


def get_connection_manager() -> ConnectionManager:
    """Returns the global instance of the ConnectionManager."""
    return manager
