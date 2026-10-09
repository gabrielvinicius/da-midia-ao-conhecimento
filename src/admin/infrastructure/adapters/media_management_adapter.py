"""Implementa MediaAdminPort sobre o módulo de mídias."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from src.admin.application.ports import MediaAdminPort
from src.media_management.application.dtos import (
    DeleteMediaCommand,
    ListMediaQuery,
    PaginatedMedia,
    ReprocessMediaCommand,
)
from src.media_management.application.services.media_service import MediaService
from src.media_management.domain.enums import MediaStatus
from src.media_management.infrastructure.repositories.media_repository import MediaRepository
from src.user_management.domain import UserRole


class MediaManagementAdapter(MediaAdminPort):
    """As ações passam pelos casos de uso do MediaService, com papel de
    administrador; a consulta de estado e a lista de falhas, pelo repositório."""

    def __init__(self, media_service: MediaService, media_repository: MediaRepository):
        self._service = media_service
        self._repo = media_repository

    async def status_of(self, media_id: UUID) -> Optional[str]:
        media = await self._repo.get_by_id(media_id)
        return media.status.value if media else None

    async def delete_media(self, media_id: UUID, actor_id: UUID) -> None:
        await self._service.delete_media(
            DeleteMediaCommand(media_id=media_id), user_id=actor_id, user_role=UserRole.ADMIN
        )

    async def reprocess_media(self, media_id: UUID, actor_id: UUID) -> None:
        await self._service.reprocess_media(
            ReprocessMediaCommand(media_id=media_id), user_id=actor_id, user_role=UserRole.ADMIN
        )

    async def failed_media_ids(self, limit: int) -> list[UUID]:
        return await self._repo.list_ids_by_status(MediaStatus.FAILED, limit)

    async def list_media(self, query: ListMediaQuery) -> PaginatedMedia:
        return await self._service.list_media(query)

    async def filenames(self, media_ids: list[UUID]) -> dict[UUID, Optional[str]]:
        found = {}
        for media_id in set(media_ids):
            media = await self._repo.get_by_id(media_id)
            if media is not None:
                found[media_id] = media.filename
        return found
