# src/notifications/api/dependencies.py
from fastapi import Request, Depends
from typing import Annotated

from src.notifications.application.commands.request_notification_command_handler import RequestNotificationCommandHandler
from src.notifications.application.queries.notification_queries import NotificationQueries
# FIXED: Should use application layer service, not direct infrastructure import
from src.shared.infrastructure.unified_notification import UnifiedNotificationService

# --- Service and Query Getters ---

def get_container(request: Request) -> dict:
    return request.app.state.container

def get_request_notification_handler(container: Annotated[dict, Depends(get_container)]) -> RequestNotificationCommandHandler:
    return container["request_notification_handler"]

def get_notification_queries(container: Annotated[dict, Depends(get_container)]) -> NotificationQueries:
    return container["notification_queries"]

# --- WebSocket Connection Manager Getter ---

def get_connection_manager() -> ConnectionManager:
    """Returns the global instance of the ConnectionManager."""
    return manager
