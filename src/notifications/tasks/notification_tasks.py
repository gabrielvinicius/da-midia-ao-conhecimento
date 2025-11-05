# src/notifications/tasks/notification_tasks.py
import asyncio
from typing import Any, Dict

import structlog
from celery import shared_task
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.notifications.application.commands.commands import SendNotificationCommand
from src.notifications.application.commands.handlers import (
    SendNotificationCommandHandler,
)
from src.notifications.application.schemas import NotificationTaskPayload
from src.notifications.config.settings import SmtpSettings
from src.notifications.infrastructure.connection_manager import (
    manager as connection_manager,  # Import the global manager
)
from src.notifications.infrastructure.notification_repository import (
    NotificationRepository,
)
from src.notifications.infrastructure.sms_adapter import SmsAdapter
from src.notifications.infrastructure.smtp_adapter import SMTPAdapter
from src.notifications.infrastructure.webhook_adapter import WebhookAdapter
from src.shared.infrastructure.database import get_db

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
        return asyncio.run(_run_notification_sending(payload))
    except Exception as e:
        logger.error(f"Error in notification task for user {user_id}: {str(e)}", exc_info=True)
        return None


async def _run_notification_sending(payload: NotificationTaskPayload):
    """Helper to run notification sending logic with manual dependency injection."""
    async for db_session in get_db():
        if not isinstance(db_session, AsyncSession):
            raise TypeError("Expected db_session to be an AsyncSession")

        # --- Manual Dependency Injection for Celery Task ---
        smtp_settings = SmtpSettings()
        adapter_map = {
            "EMAIL": SMTPAdapter(host=smtp_settings.smtp_host, port=smtp_settings.smtp_port, username=smtp_settings.smtp_user, password=smtp_settings.smtp_password),
            "SMS": SmsAdapter(),
            "WEBHOOK": WebhookAdapter(),
        }
        notification_repository = NotificationRepository(db=db_session)

        # 1. Create the command handler with all dependencies
        handler = SendNotificationCommandHandler(
            adapter_map=adapter_map,
            notification_repository=notification_repository,
            connection_manager=connection_manager # Inject the connection manager
        )

        # 2. Create the command
        command = SendNotificationCommand(
            user_id=payload.user_id,
            message=payload.message,
            notification_type=payload.notification_type,
            contact_info=payload.contact_info,
        )

        # 3. Execute the handler
        try:
            await handler.handle(command)
        except Exception as e:
            logger.error(
                "notifications.task_failed",
                user_id=payload.user_id,
                error=str(e),
                exc_info=True,
            )
            raise
