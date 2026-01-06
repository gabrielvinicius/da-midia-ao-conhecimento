"""Media Queries Service.

Provides read-only access to Media statistics and data.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from src.media_management.application.ports import MediaRepositoryPort
from src.media_management.domain import Media
from src.media_management.domain.enums import MediaStatus, MediaType

from ..dtos import (
    GetMediaQuery,
    GetMediaStatisticsQuery,
    ListMediaQuery,
    PaginatedMedia,
)


class MediaReadService:
    """Read-side facade for Media data (CQRS consulta)."""

    def __init__(self, media_repository: MediaRepositoryPort) -> None:
        self.repository = media_repository

    async def get_media(self, query: GetMediaQuery) -> Optional[Media]:
        """Retrieves a single media entity."""
        return await self.repository.get_by_id(query.media_id)

    async def list_media(self, query: ListMediaQuery) -> PaginatedMedia:
        """Lists media entities with pagination and filtering."""
        items = await self.repository.list_paginated(
            page=query.page,
            limit=query.limit,
            user_id=query.user_id,
            status=query.status,
            search=query.search,
            order=query.order,
        )
        total = await self.repository.count_filtered(
            user_id=query.user_id, status=query.status, search=query.search
        )
        pages = (total + query.limit - 1) // query.limit if query.limit else 1
        return PaginatedMedia(
            items=items,
            total=total,
            page=query.page,
            pages=pages,
            limit=query.limit,
        )

    async def get_media_statistics(
        self, query: GetMediaStatisticsQuery
    ) -> Dict[str, Any]:
        """Returns statistics about media entities."""
        if query.user_id:
            total = await self.repository.count_by_user(query.user_id)
            by_status = {
                status.value: await self.repository.count_by_user_and_status(
                    query.user_id, status
                )
                for status in MediaStatus
            }
            by_type = {
                mt.value: await self.repository.count_by_user_and_type(
                    query.user_id, mt
                )
                for mt in MediaType
            }
        else:
            total = await self.repository.count_all()
            by_status = {
                status.value: await self.repository.count_by_status(status)
                for status in MediaStatus
            }
            by_type = {
                mt.value: await self.repository.count_by_type(mt) for mt in MediaType
            }

        return {"total": total, "by_status": by_status, "by_type": by_type}

    async def count_all(self) -> int:
        """Count all media items."""
        return await self.repository.count_all()

    async def count_by_status(self, status: MediaStatus) -> int:
        """Count media items by status."""
        return await self.repository.count_by_status(status)

    async def count_by_user(self, user_id: UUID) -> int:
        """Count media items for a specific user."""
        return await self.repository.count_by_user(user_id)

    async def count_by_user_and_status(self, user_id: UUID, status: MediaStatus) -> int:
        """Count media items for a specific user and status."""
        return await self.repository.count_by_user_and_status(user_id, status)
