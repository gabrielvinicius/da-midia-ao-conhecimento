# src/media_management/application/queries/media_queries.py
from typing import Optional, List
from uuid import UUID

from src.media_management.domain.media import Media
from src.media_management.infrastructure.media_repository import MediaRepository


class MediaQueries:
    """Handles all read-only operations for media."""
    def __init__(self, media_repository: MediaRepository):
        self.media_repository = media_repository

    async def get_by_id(self, media_id: str) -> Optional[Media]:
        """Retrieves a media entity by its unique ID."""
        return await self.media_repository.find_by_id(media_id)

    async def list_by_user(self, user_id: str) -> List[Media]:
        """Lists all media for a specific user."""
        # This method needs to be updated in the repository to support pagination
        return await self.media_repository.list_by_user(user_id)

    async def list_all(self, page: int = 1, limit: int = 10, search: Optional[str] = None) -> List[Media]:
        """Lists all media in the system with pagination and search."""
        return await self.media_repository.list_all(page=page, limit=limit, search=search)
