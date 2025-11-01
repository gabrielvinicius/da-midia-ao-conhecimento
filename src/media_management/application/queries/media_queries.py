# src/media_management/application/queries/media_queries.py
from typing import List, Optional
from uuid import UUID

from src.media_management.domain.enums import MediaStatus
from src.media_management.domain.media import Media
from src.media_management.infrastructure.media_repository import MediaRepository


class MediaQueries:
    """Handles all read-only operations for media."""

    def __init__(self, media_repository: MediaRepository):
        self.media_repository = media_repository

    async def get_by_id(self, media_id: UUID) -> Optional[Media]:
        """Retrieves a media entity by its unique ID."""

        return await self.media_repository.get_by_id(media_id)

    async def list_all(
        self,
        page: int = 1,
        limit: int = 10,
        user_id: Optional[UUID] = None,
        status: Optional[MediaStatus] = None,
        search: Optional[str] = None,
    ) -> List[Media]:
        """Lists media entries with pagination and optional filters."""

        return await self.media_repository.list_paginated(
            page=page,
            limit=limit,
            user_id=user_id,
            status=status,
            search=search,
        )

    async def count_all(self) -> int:
        return await self.media_repository.count_all()

    async def count_by_status(self, status: MediaStatus) -> int:
        return await self.media_repository.count_by_status(status)

    async def count_by_user(self, user_id: UUID) -> int:
        return await self.media_repository.count_by_user(user_id)

    async def count_by_user_and_status(self, user_id: UUID, status: MediaStatus) -> int:
        return await self.media_repository.count_by_user_and_status(user_id, status)
