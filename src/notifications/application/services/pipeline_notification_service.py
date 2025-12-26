from __future__ import annotations

import time
from typing import Any, Dict, Optional
from uuid import UUID

import structlog

from src.notifications.application.ports import (
    NotificationDeliveryPort,
    NotificationLoggerPort,
    NotificationMetricsPort,
    NotificationRepositoryPort,
)
from src.notifications.domain import Notification, NotificationType
from src.notifications.domain.entities.notification import NotificationPriority

logger = structlog.get_logger(__name__)


class PipelineNotificationService:
    """Serviço mínimo para notificar o usuário sobre eventos do pipeline.

    Motivo: eventos do pipeline acontecem no worker e precisam ser refletidos no
    frontend via WebSocket (decisão 2). Aqui persistimos a notificação e
    publicamos para entrega realtime via um `NotificationDeliveryPort` (ex.: Redis).
    """

    def __init__(
        self,
        *,
        notification_repo: NotificationRepositoryPort,
        delivery: NotificationDeliveryPort,
        notification_logger: NotificationLoggerPort,
        notification_metrics: NotificationMetricsPort,
    ) -> None:
        self._repo = notification_repo
        self._delivery = delivery
        self._logger = notification_logger
        self._metrics = notification_metrics

    async def notify(
        self,
        *,
        user_id: UUID,
        message: str,
        correlation_id: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
    ) -> UUID:
        start = time.monotonic()
        success = False
        error: Exception | None = None

        notification = Notification(
            user_id=user_id,
            type=NotificationType.WEBSOCKET,
            content=message,
            priority=priority,
            variables=variables or {},
        )

        if correlation_id:
            notification.variables["correlation_id"] = correlation_id

        try:
            saved = await self._repo.save(notification)
            payload = {
                "notification_id": str(saved.id),
                "type": saved.type.value,
                "message": saved.content,
                "priority": saved.priority.value,
                "created_at": saved.created_at,
                "variables": saved.variables,
            }
            await self._delivery.send_to_user(user_id, payload)
            saved.mark_as_sent()
            # Em adapters SQLAlchemy, o segundo save deve ser merge/upsert; garantimos no repo.
            saved = await self._repo.save(saved)
            success = True
            return saved.id
        except Exception as exc:
            error = exc
            logger.error(
                "pipeline_notification.failed",
                user_id=str(user_id),
                error=str(exc),
            )
            raise
        finally:
            await self._logger.log_operation(
                operation="pipeline_notify",
                success=success,
                duration=time.monotonic() - start,
                user_id=str(user_id),
                error=error,
            )
            try:
                if success:
                    await self._metrics.record_notification_sent(channel="websocket")
            except Exception:
                return


__all__ = ["PipelineNotificationService"]
