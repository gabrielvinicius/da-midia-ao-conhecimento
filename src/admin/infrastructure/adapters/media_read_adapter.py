from __future__ import annotations

from uuid import UUID

from src.admin.application.ports import AdminMediaReadPort
from src.media_management.application.services.media_read_service import (
    MediaReadService,
)
from src.shared.domain.enums import MediaStatus


class MediaReadAdapter(AdminMediaReadPort):
    """Adapter exposing read-only media queries to the admin façade (CQRS read side)."""

    def __init__(self, media_read_service: MediaReadService) -> None:
        self._svc = media_read_service

    async def count_all(self) -> int:
        return await self._svc.count_all()

    async def count_by_status(self, status: MediaStatus) -> int:
        return await self._svc.count_by_status(status)

    async def count_by_user(self, user_id: UUID) -> int:
        return await self._svc.count_by_user(user_id)

    async def count_by_user_and_status(self, user_id: UUID, status: MediaStatus) -> int:
        return await self._svc.count_by_user_and_status(user_id, status)


__all__ = ["MediaReadAdapter"]
