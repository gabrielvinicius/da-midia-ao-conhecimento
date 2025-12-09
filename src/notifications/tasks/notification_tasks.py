# src/notifications/tasks/notification_tasks.py
from typing import Any, Dict
import asyncio
import structlog
from celery import shared_task
from pydantic import ValidationError

from src.notifications.application.schemas import NotificationTaskPayload
from src.notifications.domain.notification import NotificationType
from src.notifications.infrastructure.notification_repository import NotificationRepository
from src.notifications.infrastructure.logging import StructuredNotificationLogger
from src.notifications.infrastructure.metrics import PrometheusNotificationMetrics
from src.notifications.infrastructure.connection_manager import manager as connection_manager_instance
from src.notifications.application.services.notification_service import NotificationService
from src.user_management.infrastructure.repositories.sqlalchemy_user_repository import UserRepository
from src.user_management.application.auth_queries import AuthQueries
from src.shared.infrastructure.database.db import get_sync_session

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
        logger.error("notifications.task_invalid_payload", user_id=user_id, errors=exc.errors())
        return None

    correlation_id = contact_info.get("correlation_id") if isinstance(contact_info, dict) else None
    
    try:
        with get_sync_session() as db_session:
            return _run_notification_sending_sync(payload, db_session, correlation_id)
    except Exception as e:
        logger.error("notifications.task_failed", user_id=user_id, error=str(e), correlation_id=correlation_id, exc_info=True)
        return None

def _run_notification_sending_sync(payload: NotificationTaskPayload, db_session, correlation_id=None):
    # Build dependencies
    notification_repo = NotificationRepository(db=db_session)
    user_repo = UserRepository(db=db_session)
    auth_queries = AuthQueries(user_repository=user_repo)
    
    service = NotificationService(
        notification_repo=notification_repo,
        connection_manager=connection_manager_instance,
        auth_queries=auth_queries,
        notification_logger=StructuredNotificationLogger(),
        notification_metrics=PrometheusNotificationMetrics(),
        email_sender=None, # Adapters not wired yet in this context, but service handles placeholder
        sms_sender=None,
        push_sender=None
    )

    try:
        notif_type = NotificationType(payload.notification_type)
    except ValueError as exc:
        logger.error("notifications.task_invalid_type", user_id=payload.user_id, error=str(exc))
        return None

    async def _async_call():
        return await service.send_notification(
            user_id=payload.user_id,
            message=payload.message,
            notification_type=notif_type,
            variables={"correlation_id": correlation_id}
        )

    try:
        result_id = asyncio.run(_async_call())
        return {
            "status": "SENT",
            "notification_id": str(result_id)
        }
    except Exception as e:
        logger.error("notifications.task_failed", user_id=payload.user_id, error=str(e), exc_info=True)
        raise