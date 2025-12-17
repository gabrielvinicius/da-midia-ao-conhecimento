from __future__ import annotations

from typing import Any

from src.notifications.application.ports import NotificationLoggerPort
from src.notifications.infrastructure.logging.structured_logger import (
    StructuredNotificationLogger,
)


class NotificationLoggerAdapter(NotificationLoggerPort):
    """Adapter to bridge StructuredNotificationLogger into the application port."""

    def __init__(self, logger: StructuredNotificationLogger | None = None) -> None:
        self._logger = logger or StructuredNotificationLogger()

    async def log_operation(
        self,
        *,
        operation: str,
        success: bool,
        duration: float,
        **extra: Any,
    ) -> None:
        # Structured logger is synchronous; call info with structured payload.
        self._logger.info(
            "notification.operation",
            operation=operation,
            success=success,
            duration=duration,
            **extra,
        )

    def info(self, message: str, **extra: Any) -> None:
        self._logger.info(message, **extra)

    def warning(self, message: str, **extra: Any) -> None:
        self._logger.warning(message, **extra)

    def error(self, message: str, **extra: Any) -> None:
        self._logger.error(message, **extra)


__all__ = ["NotificationLoggerAdapter"]
