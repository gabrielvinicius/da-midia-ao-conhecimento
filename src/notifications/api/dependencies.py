# src/notifications/api/dependencies.py
from fastapi import Request, Depends
from typing import Annotated

from src.notifications.application.notification_service import NotificationService
from src.notifications.application.queries.notification_queries import NotificationQueries

# --- Service and Query Getters ---

def get_container(request: Request) -> dict:
    return request.app.state.container

def get_notification_service(container: Annotated[dict, Depends(get_container)]) -> NotificationService:
    return container["notification_service"]

def get_notification_queries(container: Annotated[dict, Depends(get_container)]) -> NotificationQueries:
    return container["notification_queries"]
