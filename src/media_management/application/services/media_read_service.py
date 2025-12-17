"""Media Queries Service.

Provides read-only access to Media statistics and data.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from src.media_management.application.ports import MediaRepositoryPort
from src.media_management.domain import Media
from src.shared.domain.enums import MediaStatus

from ..dtos import (
    GetMediaQuery,
    GetMediaStatisticsQuery,
    ListMediaQuery,
)


class MediaReadService:
    """Read-side facade for Media data (CQRS consulta)."""

    def __init__(self, media_repository: MediaRepositoryPort) -> None:
        self.repository = media_repository

    async def get_media(self, query: GetMediaQuery) -> Optional[Media]:
        """Retrieves a single media entity."""
        return await self.repository.get_by_id(query.media_id)

    async def list_media(self, query: ListMediaQuery) -> List[Media]:
        """Lists media entities with pagination and filtering."""
        return await self.repository.list_paginated(
            page=query.page,
            limit=query.limit,
            user_id=query.user_id,
            status=query.status,
            search=query.search,
        )

    async def get_media_statistics(
        self, query: GetMediaStatisticsQuery
    ) -> Dict[str, Any]:
        """Returns statistics about media entities."""
        if query.user_id:
            total = await self.repository.count_by_user(query.user_id)
            by_status = {}
            for status in MediaStatus:
                count = await self.repository.count_by_user_and_status(
                    query.user_id, status
                )
                by_status[status.value] = count
        else:
            total = await self.repository.count_all()
            by_status = {}
            for status in MediaStatus:
                count = await self.repository.count_by_status(status)
                by_status[status.value] = count

        return {"total": total, "by_status": by_status}

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
