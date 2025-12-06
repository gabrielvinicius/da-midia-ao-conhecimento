"""Adapters that expose legacy media management features to the admin façade."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

import math

from src.media_management.application.services.media_service import MediaService
from src.media_management.application.queries.dto import ListMediaQuery, GetMediaStatisticsQuery
from src.user_management.domain.user import User


@dataclass(slots=True)
class MediaManagementAdapter:
    """Wrapper around media queries and admin media service used by the façade."""

    media_service: MediaService
    admin_media_service: AdminMediaService

    async def list_media(
        self,
        *,
        page: int,
        limit: int,
        search: Optional[str],
    ):
        list_query = ListMediaQuery(page=page, limit=limit, search=search)
        items = await self.media_service.list_media(query=list_query)
        
        count_query = GetMediaStatisticsQuery(search=search)
        statistics = await self.media_service.get_media_statistics(query=count_query)
        total_items = statistics.get("total", 0)
        
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
