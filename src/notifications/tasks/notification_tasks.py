# src/notifications/tasks/notification_tasks.py
from typing import Any, Dict

import asyncio

import structlog
from celery import shared_task
from pydantic import ValidationError

from src.notifications.application.commands.commands import SendNotificationCommand
from src.notifications.application.commands.handlers import (
    SendNotificationCommandHandler,
)
from src.notifications.application.schemas import NotificationTaskPayload
from src.notifications.config.settings import SmtpSettings
from src.notifications.domain.notification import NotificationType
from src.notifications.infrastructure.notification_repository import (
    NotificationRepository,
)
from src.notifications.infrastructure.sms_adapter import SmsAdapter
from src.notifications.infrastructure.smtp_adapter import SMTPAdapter
from src.notifications.infrastructure.webhook_adapter import WebhookAdapter
from src.shared.infrastructure.database import get_sync_session
from src.user_management.infrastructure.user_repository import UserRepository

logger = structlog.get_logger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_notification_task(self, user_id: str, message: str, notification_type: str, contact_info: Dict[str, Any]):
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

    try:
        with get_sync_session() as db_session:
            return _run_notification_sending_sync(payload, db_session)
    except Exception as e:
        logger.error(f"Error in notification task for user {user_id}: {str(e)}", exc_info=True)
        return None


def _run_notification_sending_sync(payload: NotificationTaskPayload, db_session):
    smtp_settings = SmtpSettings()
    handler = SendNotificationCommandHandler(
        email_adapter=SMTPAdapter(
            host=smtp_settings.smtp_host,
            port=smtp_settings.smtp_port,
            username=smtp_settings.smtp_user,
            password=smtp_settings.smtp_password,
        ),
        sms_adapter=SmsAdapter(),
        webhook_adapter=WebhookAdapter(),
        notification_repository=NotificationRepository(db=db_session),
        user_repository=UserRepository(db_session),
    )

    try:
        notification_type = NotificationType(payload.notification_type)
    except ValueError as exc:
        logger.error(
            "notifications.task_invalid_type",
            user_id=payload.user_id,
            notification_type=payload.notification_type,
            error=str(exc),
        )
        return None

    command = SendNotificationCommand(
        user_id=payload.user_id,
        message=payload.message,
        notification_type=notification_type,
    )

    try:
        result = asyncio.run(handler.handle(command))
        return {
            "status": result.status.value,
            "error": result.error_message,
        }
    except Exception as e:
        logger.error(
            "notifications.task_failed",
            user_id=payload.user_id,
            error=str(e),
            exc_info=True,
        )
        raise
