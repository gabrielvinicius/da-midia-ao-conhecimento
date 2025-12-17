"""Bootstrap helpers for notifications tasks."""
from __future__ import annotations

from typing import Any

from src.notifications.application.services.notification_service import (
    NotificationService,
)
from src.notifications.infrastructure.dependencies.providers import (
    get_auth_queries,
    get_connection_manager,
    get_email_sender,
    get_push_sender,
    get_sms_sender,
)
from src.notifications.infrastructure.logging.structured_logger import (
    StructuredNotificationLogger,
)
from src.notifications.infrastructure.metrics.prometheus_metrics import (
    PrometheusNotificationMetrics,
)
from src.notifications.infrastructure.repositories.notification_repository import (
    NotificationRepository,
)


def build_notification_service(db_session: Any) -> NotificationService:
    """Compose NotificationService with current adapters/ports."""
    notification_repo = NotificationRepository(db=db_session)
    auth_queries = get_auth_queries(db_session)
    return NotificationService(
        notification_repo=notification_repo,
        connection_manager=get_connection_manager(),
        auth_queries=auth_queries,
        notification_logger=StructuredNotificationLogger(),
        notification_metrics=PrometheusNotificationMetrics(),
        email_sender=get_email_sender(),
        sms_sender=get_sms_sender(),
        push_sender=get_push_sender(),
    )


__all__ = ["build_notification_service"]
