"""Apaga os avisos de um usuário que será excluído (UserDataEraserPort)."""
from __future__ import annotations

from uuid import UUID

from src.notifications.infrastructure.repositories.notification_repository import (
    NotificationRepository,
)


class UserNotificationsEraser:
    name = "notifications"

    def __init__(self, repository: NotificationRepository) -> None:
        self._repository = repository

    async def erase(self, user_id: UUID) -> None:
        await self._repository.delete_by_user(user_id)


__all__ = ["UserNotificationsEraser"]
