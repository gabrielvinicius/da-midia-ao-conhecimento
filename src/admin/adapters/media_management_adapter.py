"""Adapters that expose legacy media management features to the admin façade."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

import math

from src.admin.application.services.admin_media_service import AdminMediaService
from src.media_management.application.facade import MediaOrchestrator
from src.user_management.domain.user import User


@dataclass(slots=True)
class MediaManagementAdapter:
    """Wrapper around media queries and admin media service used by the façade."""

    media_orchestrator: MediaOrchestrator
    admin_media_service: AdminMediaService

    async def list_media(
        self,
        *,
        page: int,
        limit: int,
        search: Optional[str],
    ):
        items = await self.media_orchestrator.queries.list_all(
            page=page,
            limit=limit,
            search=search,
        )
        total_items = await self.media_orchestrator.queries.count_filtered(search=search)
        total_pages = math.ceil(total_items / limit) if limit else 1
        return {
            "items": items,
            "total_items": total_items,
            "total_pages": total_pages,
            "current_page": page,
        }

    async def delete_media(self, *, media_id: UUID, admin_user: User) -> None:
        await self.admin_media_service.delete_media(media_id, admin_user)

    async def reprocess_media(self, *, media_id: UUID, admin_user: User) -> None:
        await self.admin_media_service.reprocess_media(media_id, admin_user)

    async def bulk_reprocess_failed_media(self, *, admin_user: User) -> int:
        return await self.admin_media_service.bulk_reprocess_failed_media(admin_user)

    async def cleanup_orphaned_files(self, *, admin_user: User) -> int:
        return await self.admin_media_service.cleanup_orphaned_files(admin_user)
