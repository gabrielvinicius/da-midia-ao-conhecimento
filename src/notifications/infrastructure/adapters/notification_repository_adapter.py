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

    async def list_by_user(self, user_id: str):
        return await self._repo.list_by_user(user_id)

    async def delete(self, notification_id: str) -> bool:
        return await self._repo.delete(str(notification_id))

    async def mark_as_read(self, notification_id: str) -> bool:
        return await self._repo.mark_as_read(str(notification_id))

    async def mark_as_delivered(self, notification_id: str) -> bool:
        return await self._repo.mark_as_delivered(str(notification_id))

    async def list_undelivered_by_user(self, user_id: str, limit: int = 50):
        return await self._repo.list_undelivered_by_user(user_id, limit=limit)

    async def count_all(self) -> int:
        return await self._repo.count_all()

    async def count_unread_all(self) -> int:
        return await self._repo.count_unread_all()

    async def count_by_user_id(self, user_id: UUID) -> int:
        return await self._repo.count_by_user_id(user_id)

    async def count_unread_by_user_id(self, user_id: UUID) -> int:
        return await self._repo.count_unread_by_user_id(user_id)

    async def delete_older_than(self, days_to_keep: int) -> int:
        return await self._repo.delete_older_than(days_to_keep)


__all__ = ["NotificationRepositoryAdapter"]
