# Celery tasks for notifications (moved to application/tasks.py)
import asyncio
from typing import Any, Dict

import structlog
from celery import shared_task
from pydantic import ValidationError

from src.notifications.application.schemas import NotificationTaskPayload
from src.notifications.application.services.notification_service import (
    NotificationService,
)
from src.notifications.application.dtos import SendNotificationCommand
from src.notifications.domain import NotificationType
from src.notifications.application.services.notification_read_service import (
    NotificationReadService,
)
from src.notifications.infrastructure.adapters.auth_queries_adapter import (
    NotificationsAuthQueriesAdapter,
)
from src.notifications.infrastructure.adapters.notification_logger_adapter import (
    NotificationLoggerAdapter,
)
from src.notifications.infrastructure.adapters.notification_metrics_adapter import (
    NotificationMetricsAdapter,
)
from src.notifications.infrastructure.adapters.notification_repository_adapter import (
    NotificationRepositoryAdapter,
)
from src.notifications.infrastructure.adapters.redis_notification_delivery_adapter import (
    RedisNotificationDeliveryAdapter,
)
from src.notifications.infrastructure.repositories.notification_repository import (
    NotificationRepository,
)
from src.shared.infrastructure.database.db import get_sync_session

logger = structlog.get_logger(__name__)

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_notification_task(
    self,
    user_id: str,
    message: str,
    notification_type: str,
    contact_info: Dict[str, Any],
):
    """Celery task to trigger the notification sending pipeline."""
    try:
        payload = NotificationTaskPayload.model_validate(
            {
                "user_id": user_id,
                "message": message,
                "notification_type": notification_type,
                "contact_info": contact_info,
            }
        )
    except ValidationError as exc:
        logger.error(
            "notifications.task_invalid_payload",
            user_id=user_id,
            errors=exc.errors(),
        )
        return None

    correlation_id = (
        contact_info.get("correlation_id")
        if isinstance(contact_info, dict)
        else None
    )

    final_attempt = (self.request.retries or 0) >= (self.max_retries or 0)
    try:
        with get_sync_session() as db_session:
            return _run_notification_sending_sync(
                payload,
                db_session,
                correlation_id=correlation_id,
                final_attempt=final_attempt,
            )
    except Exception as e:
        logger.error(
            "notifications.task_failed",
            user_id=user_id,
            error=str(e),
            correlation_id=correlation_id,
            exc_info=True,
        )
        return None

def _run_notification_sending_sync(
    payload: NotificationTaskPayload,
    db_session,
    correlation_id=None,
    final_attempt: bool = False,
):
    repo = NotificationRepository(db=db_session)
    repo_adapter = NotificationRepositoryAdapter(repo)
    read_service = NotificationReadService(notification_repo=repo_adapter)
    auth_queries = NotificationsAuthQueriesAdapter(db_session=db_session)
    service = NotificationService(
        notification_repo=repo_adapter,
        delivery=RedisNotificationDeliveryAdapter(),
        auth_queries=auth_queries,
        notification_logger=NotificationLoggerAdapter(),
        notification_metrics=NotificationMetricsAdapter(),
        notification_read_service=read_service,
    )

    try:
        notif_type = NotificationType(payload.notification_type)
    except ValueError as exc:
        logger.error(
            "notifications.task_invalid_type",
            user_id=payload.user_id,
            error=str(exc),
        )
        return None

    async def _async_call():
        command = SendNotificationCommand(
            user_id=payload.user_id,
            message=payload.message,
            notification_type=notif_type,
            variables={"correlation_id": correlation_id},
        )
        return await service.send_notification(
            command,
            final_attempt=final_attempt,
        )

    try:
        result_id = asyncio.run(_async_call())
        return {
            "status": "SENT",
            "notification_id": str(result_id)
        }
    except Exception as e:
        logger.error(
            "notifications.task_failed",
            user_id=payload.user_id,
            error=str(e),
            exc_info=True,
        )
        raise
