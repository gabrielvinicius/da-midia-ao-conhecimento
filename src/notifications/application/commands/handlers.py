"""Legacy command handlers retained for backwards compatibility."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Optional
from uuid import UUID

from src.notifications.application.commands.commands import (
    RequestNotificationCommand,
    SendNotificationCommand,
)
from src.notifications.domain.notification import (
    Notification,
    NotificationStatus,
    NotificationType,
)
from src.shared.events.domain_events import NotificationRequested


async def _await_call(func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any) -> Any:
    return await func(*args, **kwargs)


class RequestNotificationCommandHandler:
    """Compatibility handler that enriches and publishes notification requests."""

    def __init__(self, *, auth_queries: Any, event_bus: Any) -> None:
        self._auth_queries = auth_queries
        self._event_bus = event_bus

    async def handle(self, command: RequestNotificationCommand) -> None:
        user = await self._auth_queries.get_by_id(command.user_id)
        if user is None:
            raise ValueError("User not found")

        contact_info: Dict[str, Any] = {}
        if getattr(user, "email", None):
            contact_info["email"] = user.email
        if getattr(user, "phone_number", None):
            contact_info["phone_number"] = user.phone_number

        event = NotificationRequested(
            user_id=str(getattr(user, "id", command.user_id)),
            message=command.message,
            notification_type=command.notification_type.value,
            contact_info=contact_info,
        )
        await self._event_bus.publish(event)


@dataclass(slots=True)
class NotificationDeliveryResult:
    status: NotificationStatus
    error_message: Optional[str] = None


class SendNotificationCommandHandler:
    """Compatibility handler that routes sending to channel adapters."""

    def __init__(
        self,
        *,
        email_adapter: Any,
        sms_adapter: Any,
        webhook_adapter: Any,
        notification_repository: Any,
        user_repository: Any,
    ) -> None:
        self._email_adapter = email_adapter
        self._sms_adapter = sms_adapter
        self._webhook_adapter = webhook_adapter
        self._notification_repository = notification_repository
        self._user_repository = user_repository

    async def handle(self, command: SendNotificationCommand) -> NotificationDeliveryResult:
        user = await self._user_repository.find_by_id(command.user_id)
        if user is None:
            raise ValueError("User not found")

        adapter = self._resolve_adapter(command.notification_type)

        try:
            await adapter(user, command)
            await self._notification_repository.save(
                Notification(
                    user_id=UUID(command.user_id),
                    type=command.notification_type,
                    content=command.message,
                    subject=command.subject or "Notification",
                    status=NotificationStatus.SENT,
                )
            )
            return NotificationDeliveryResult(status=NotificationStatus.SENT)
        except Exception as exc:  # pragma: no cover - defensive safety
            await self._notification_repository.save(
                Notification(
                    user_id=UUID(command.user_id),
                    type=command.notification_type,
                    content=command.message,
                    subject=command.subject or "Notification",
                    status=NotificationStatus.FAILED,
                    error_message=str(exc),
                )
            )
            return NotificationDeliveryResult(
                status=NotificationStatus.FAILED,
                error_message=str(exc),
            )

    def _resolve_adapter(
        self,
        notification_type: NotificationType,
    ) -> Callable[[Any, SendNotificationCommand], Awaitable[None]]:
        if notification_type == NotificationType.EMAIL:

            async def send_email(user: Any, command: SendNotificationCommand) -> None:
                await _await_call(
                    self._email_adapter.send,
                    getattr(user, "email", None),
                    command.subject or "Notification",
                    command.message,
                )

            return send_email

        if notification_type == NotificationType.SMS:

            async def send_sms(user: Any, command: SendNotificationCommand) -> None:
                await _await_call(
                    self._sms_adapter.send,
                    getattr(user, "phone_number", None),
                    command.message,
                )

            return send_sms

        async def send_webhook(user: Any, command: SendNotificationCommand) -> None:
            await _await_call(
                self._webhook_adapter.send,
                command.message,
                metadata={"user_id": getattr(user, "id", None)},
            )

        return send_webhook


__all__ = [
    "RequestNotificationCommandHandler",
    "SendNotificationCommandHandler",
    "NotificationDeliveryResult",
]
