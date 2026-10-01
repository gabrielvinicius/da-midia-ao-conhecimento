# Tarefas Celery de notificações (camada de montagem do módulo).
import asyncio
from typing import Any, Dict

import structlog
from celery import shared_task
from pydantic import ValidationError

from src.notifications.application.schemas import NotificationTaskPayload
from src.notifications.application.dtos import SendNotificationCommand
from src.notifications.domain import NotificationType
from src.notifications.bootstrap import bootstrap_task_service
from src.shared.infrastructure.database.db import get_sync_session

logger = structlog.get_logger(__name__)

@shared_task(
    bind=True, name="notifications.send", autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
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
    # Use the bootstrap helper to create the service with correct dependencies
    service = bootstrap_task_service(db_session)

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
        # Merge contact_info into variables, preserving correlation_id
        variables = payload.contact_info.copy()
        if correlation_id:
            variables["correlation_id"] = correlation_id

        command = SendNotificationCommand(
            user_id=payload.user_id,
            message=payload.message,
            notification_type=notif_type,
            variables=variables,
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