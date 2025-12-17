"""Repositório em memória para o contexto de media management (para testes)."""
from __future__ import annotations

from typing import Dict, List, Optional
from uuid import UUID, uuid4

from src.media_management.application.ports import MediaRepositoryPort
from src.media_management.domain import Media
from src.shared.domain.enums import MediaStatus


class FakeMediaRepository(MediaRepositoryPort):
    def __init__(self) -> None:
        self._items: Dict[UUID, Media] = {}

    async def get_by_id(self, media_id: UUID) -> Optional[Media]:
        return self._items.get(media_id)

    async def save(self, media: Media) -> Media:
        if media.id is None:
            media.id = uuid4()
        self._items[media.id] = media
        return media

    async def delete(self, media_id: UUID) -> None:
        self._items.pop(media_id, None)

    async def update(self, media: Media) -> Media:
        self._items[media.id] = media
        return media

    async def count_all(self) -> int:
        return len(self._items)

    async def count_by_user(self, user_id: UUID) -> int:
        return sum(1 for m in self._items.values() if m.user_id == user_id)

    async def count_by_status(self, status: MediaStatus) -> int:
        return sum(1 for m in self._items.values() if m.status == status)

    async def count_by_user_and_status(
        self, user_id: UUID, status: MediaStatus
    ) -> int:
        return sum(
            1
            for m in self._items.values()
            if m.user_id == user_id and m.status == status
        )

    async def list_paginated(
        self,
        page: int = 1,
        limit: int = 10,
        user_id: Optional[UUID] = None,
        status: Optional[MediaStatus] = None,
        search: Optional[str] = None,
    ) -> List[Media]:
        items = list(self._items.values())
        if user_id:
            items = [m for m in items if m.user_id == user_id]
        if status:
            items = [m for m in items if m.status == status]
        if search:
            items = [m for m in items if search.lower() in (m.filename or "").lower()]
        start = (page - 1) * limit
        end = start + limit
        return items[start:end]


__all__ = ["FakeMediaRepository"]
