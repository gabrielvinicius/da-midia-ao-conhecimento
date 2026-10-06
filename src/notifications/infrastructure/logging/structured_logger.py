"""Lightweight structured logger for notification-related events."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.shared.application.observability import LoggerPort


class StructuredNotificationLogger(LoggerPort):
    """Logger simples que emite mensagens estruturadas via stdlib logging."""

    def __init__(self) -> None:
        self._logger = logging.getLogger("notifications")

    def info(self, message: str, **extra: Any) -> None:
        self._logger.info(message, extra=self._format_extra(extra))

    def warning(self, message: str, **extra: Any) -> None:
        self._logger.warning(message, extra=self._format_extra(extra))

    def error(
        self,
        message: str,
        *,
        exc: Optional[BaseException] = None,
        **extra: Any,
    ) -> None:
        self._logger.error(
            message,
            exc_info=exc,
            extra=self._format_extra(extra),
        )

    async def log_operation(self, **kwargs) -> None:
        self._logger.info("notification.operation", extra=self._format_extra(kwargs))

    @staticmethod
    def _format_extra(extra: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure we always pass a dict to logging handlers."""
        return {"notification": extra} if extra else {}


__all__ = ["StructuredNotificationLogger"]
