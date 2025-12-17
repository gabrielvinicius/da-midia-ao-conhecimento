"""Helpers for dispatching media-related notifications."""

from __future__ import annotations

from uuid import UUID

import structlog

from src.notifications.domain import NotificationType
from src.notifications.application.tasks import send_notification_task
from src.shared.domain.enums import MediaStatus

logger = structlog.get_logger(__name__)


def enqueue_media_status_notification(
    *,
    user_id: UUID,
    media_id: UUID,
    status: MediaStatus,
    error_message: str | None = None,
) -> None:
    """Schedule a websocket notification reflecting the media status."""
    status_value = status.value if isinstance(status, MediaStatus) else str(status)

    if status_value == MediaStatus.COMPLETED.value:
        message = "Sua mídia foi processada com sucesso."
    elif status_value == MediaStatus.FAILED.value:
        message = "Falha ao processar sua mídia."
    elif status_value == MediaStatus.PROCESSING.value:
        message = "Sua mídia está em processamento."
    else:
        message = f"Status da mídia atualizado para {status_value}."

    if error_message:
        message = f"{message} Detalhes: {error_message}"

    payload = {
        "kind": "MEDIA_STATUS",
        "media_id": str(media_id),
        "status": status_value,
        "error": error_message,
    }

    try:
        send_notification_task.delay(
            str(user_id),
            message,
            NotificationType.WEBSOCKET.value,
            payload,
        )
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.warning(
            "notifications.dispatch.failed",
            media_id=str(media_id),
            user_id=str(user_id),
            status=status_value,
            error=str(exc),
        )


__all__ = ["enqueue_media_status_notification"]
