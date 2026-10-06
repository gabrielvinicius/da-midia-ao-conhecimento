from __future__ import annotations

from typing import Any, List, Optional, Protocol
from uuid import UUID

from src.notifications.domain import Notification
from src.shared.application.observability import (
    MetricsPort as SharedMetricsPort,
)


class NotificationRepositoryPort(Protocol):
    async def find_by_id(self, notification_id: UUID) -> Optional[Notification]: ...
    async def save(self, notification: Notification) -> Notification: ...
    async def list_by_user(self, user_id: str, limit: int = 50, unread_only: bool = False): ...
    async def mark_all_as_read(self, user_id: str) -> int: ...
    async def list_undelivered_by_user(self, user_id: str, limit: int = 50) -> List[Notification]: ...
    async def mark_as_delivered(self, notification_id: UUID) -> bool: ...


class NotificationDeliveryPort(Protocol):
    async def send_to_user(self, user_id: UUID, payload: Any) -> bool: ...


class NotificationLoggerPort(Protocol):
    async def log_operation(
        self,
        *,
        operation: str,
        success: bool,
        duration: float,
        **extra: Any,
    ) -> None: ...
    def info(self, message: str, **extra: Any) -> None: ...
    def warning(self, message: str, **extra: Any) -> None: ...
    def error(self, message: str, **extra: Any) -> None: ...


class NotificationMetricsPort(SharedMetricsPort, Protocol):
    async def record_notification_sent(self, channel: str) -> None: ...


__all__ = [
    "NotificationRepositoryPort",
    "NotificationDeliveryPort",
    "NotificationLoggerPort",
    "NotificationMetricsPort",
]
