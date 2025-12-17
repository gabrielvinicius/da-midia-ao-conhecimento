from __future__ import annotations

from uuid import UUID

from src.media_management.application.ports import MediaRepositoryPort
from src.media_management.domain import Media
from src.media_management.infrastructure.repositories.media_repository import (
    MediaRepository,
)


class MediaRepositoryAdapter(MediaRepositoryPort):
    def __init__(self, repo: MediaRepository):
        self._repo = repo

    async def get_by_id(self, media_id: UUID):
        return await self._repo.get_by_id(media_id)

    async def save(self, media: Media):
        return await self._repo.save(media)

    async def delete(self, media_id: UUID):
        return await self._repo.delete(media_id)

    async def update(self, media: Media):
        return await self._repo.update(media)

    async def count_all(self) -> int:
        return await self._repo.count_all()

    async def count_by_user(self, user_id: UUID) -> int:
        return await self._repo.count_by_user(user_id)

    async def count_by_status(self, status):
        return await self._repo.count_by_status(status)

    async def count_by_user_and_status(self, user_id: UUID, status):
        return await self._repo.count_by_user_and_status(user_id, status)

    async def list_paginated(self, page: int, limit: int):
        return await self._repo.list_paginated(page=page, limit=limit)


__all__ = ["MediaRepositoryAdapter"]
