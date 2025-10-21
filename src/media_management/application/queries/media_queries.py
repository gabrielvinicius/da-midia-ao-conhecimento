# src/media_management/application/queries/media_queries.py
from typing import Optional, List
from uuid import UUID

from src.media_management.domain.media import Media
# FIXED: Application should not import Infrastructure directly
from src.shared.application.dependency_injection import get_media_repository


class MediaQueries:
    """Handles all read-only operations for media."""
    def __init__(self, media_repository: MediaRepository):
        self.media_repository = media_repository

    async def get_by_id(self, media_id: str) -> Optional[Media]:
        """Retrieves a media entity by its unique ID."""
        return await self.media_repository.find_by_id(media_id)

    async def list_by_user(self, user_id: str, page: int = 1, limit: int = 100) -> List[Media]:
        """Lists all media for a specific user."""
        media_list, total_count = await self.media_repository.list_by_user(user_id, page=page, limit=limit)
        return media_list

    async def list_all(self, page: int = 1, limit: int = 10, search: Optional[str] = None) -> List[Media]:
        """Lists all media in the system with pagination and search."""
        media_list, total_count = await self.media_repository.list_all(page=page, limit=limit, search=search)
        return media_list
