# src/media_management/application/queries/media_queries.py
from typing import Optional, List
from uuid import UUID

from src.media_management.domain.media import Media
from src.media_management.infrastructure.media_repository import MediaRepository
from src.media_management.domain.enums import MediaStatus


class MediaQueries:
    """Handles all read-only operations for media."""
    def __init__(self, media_repository: MediaRepository):
        self.media_repository = media_repository

    async def get_by_id(self, media_id: UUID) -> Optional[Media]:
        """Retrieves a media entity by its unique ID."""
        return await self.media_repository.get_by_id(media_id)

    async def list_all(self, user_id: Optional[UUID] = None, status: Optional[MediaStatus] = None) -> List[Media]:
        """Lists all media, optionally filtered by user_id or status."""
        return await self.media_repository.list_all(user_id=user_id, status=status)