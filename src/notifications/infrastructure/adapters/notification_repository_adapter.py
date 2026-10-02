from __future__ import annotations

from typing import Optional
from uuid import UUID

from src.notifications.application.ports import NotificationRepositoryPort
from src.notifications.domain import Notification
from src.notifications.infrastructure.repositories.notification_repository import (
    NotificationRepository,
)


class NotificationRepositoryAdapter(NotificationRepositoryPort):
    def __init__(self, repo: NotificationRepository):
        self._repo = repo

    async def find_by_id(self, notification_id: UUID) -> Optional[Notification]:
        return await self._repo.find_by_id(str(notification_id))

    async def save(self, notification: Notification) -> Notification:
        return await self._repo.save(notification)

    async def list_by_user(self, user_id: str, limit: int = 50):
        return await self._repo.list_by_user(user_id, limit=limit)

    async def mark_all_as_read(self, user_id: str) -> int:
        return await self._repo.mark_all_as_read(user_id)



__all__ = ["NotificationRepositoryAdapter"]
