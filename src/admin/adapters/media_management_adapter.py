"""Adapters that expose legacy media management features to the admin façade."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from src.auth.domain.user import User
from src.media_management.application.facade import MediaManagementFacade
from src.admin.application.services.admin_media_service import AdminMediaService


@dataclass(slots=True)
class MediaManagementAdapter:
    """Wrapper around media queries and admin media service used by the façade."""

    media_facade: MediaManagementFacade
    admin_media_service: AdminMediaService

    async def list_media(
        self,
        *,
        page: int,
        limit: int,
        search: Optional[str],
    ):
        return await self.media_facade.list_media(
            page=page,
            limit=limit,
            search=search,
        )

    async def delete_media(self, *, media_id: UUID, admin_user: User) -> None:
        await self.admin_media_service.delete_media(media_id, admin_user)

    async def reprocess_media(self, *, media_id: UUID, admin_user: User) -> None:
        await self.admin_media_service.reprocess_media(media_id, admin_user)

    async def bulk_reprocess_failed_media(self, *, admin_user: User) -> int:
        return await self.admin_media_service.bulk_reprocess_failed_media(admin_user)

    async def cleanup_orphaned_files(self, *, admin_user: User) -> int:
        return await self.admin_media_service.cleanup_orphaned_files(admin_user)
