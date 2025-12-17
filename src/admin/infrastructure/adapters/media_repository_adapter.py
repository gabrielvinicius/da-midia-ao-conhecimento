from __future__ import annotations

from src.admin.application.ports import AdminMediaRepositoryPort
from src.media_management.infrastructure.repositories.media_repository import (
    MediaRepository,
)


class MediaRepositoryAdapter(AdminMediaRepositoryPort):
    def __init__(self, repo: MediaRepository):
        self._repo = repo

    async def get_by_id(self, media_id):
        return await self._repo.get_by_id(media_id)

    async def update(self, media):
        return await self._repo.update(media)

    async def delete(self, media_id):
        return await self._repo.delete(media_id)

    async def list_paginated(self, page: int, limit: int):
        return await self._repo.list_paginated(page=page, limit=limit)


__all__ = ["MediaRepositoryAdapter"]
