from dataclasses import dataclass
from typing import Optional

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from src.notifications.api.dependencies import get_notification_service
from src.notifications.application.ports import AuthQueriesPort, NotificationDeliveryPort
from src.notifications.application.services.notification_service import (
    NotificationService,
)
from src.notifications.application.services.pipeline_notification_service import (
    PipelineNotificationService,
)
from src.notifications.infrastructure.adapters.notification_delivery_adapter import (
    WebSocketNotificationDeliveryAdapter,
)
from src.notifications.infrastructure.dependencies.builders import (
    build_notification_service,
    build_pipeline_notification_service,
)


@dataclass
class NotificationsModule:
    service: NotificationService


def build_notifications_module(
    session: AsyncSession,
    auth_queries: AuthQueriesPort,
    event_bus=None,
    delivery_adapter: Optional[NotificationDeliveryPort] = None,
) -> NotificationsModule:
    """Módulo da API: entrega pelo WebSocket do navegador."""
    return NotificationsModule(
        service=build_notification_service(
            session,
            delivery=delivery_adapter or WebSocketNotificationDeliveryAdapter(),
            auth_queries=auth_queries,
        )
    )


def bootstrap_pipeline_notification_service(session) -> PipelineNotificationService:
    return build_pipeline_notification_service(session)


def bind_notifications_module(app: FastAPI, module: NotificationsModule) -> None:
    app.dependency_overrides[get_notification_service] = lambda: module.service


__all__ = [
    "NotificationsModule",
    "build_notifications_module",
    "bootstrap_pipeline_notification_service",
    "bind_notifications_module",
]
