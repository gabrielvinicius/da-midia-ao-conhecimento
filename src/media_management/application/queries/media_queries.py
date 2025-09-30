# src/media_management/application/queries/media_queries.py
import math
from typing import Optional, List
from uuid import UUID

from src.media_management.domain.media import Media
from src.media_management.infrastructure.media_repository import MediaRepository
from src.shared.api.schemas import PaginatedResponse


class MediaQueries:
    """Handles all read-only operations for media."""
    def __init__(self, media_repository: MediaRepository):
        self.media_repository = media_repository

    async def get_by_id(self, media_id: str) -> Optional[Media]:
        """Retrieves a media entity by its unique ID."""
        return await self.media_repository.find_by_id(media_id)

    async def list_by_user(self, user_id: str) -> List[Media]:
        """Lists all media for a specific user."""
        return await self.media_repository.list_by_user(user_id)

    async def list_all(self, page: int, limit: int, search: Optional[str]) -> PaginatedResponse[Media]:
        """Lists all media in the system with pagination and search. For admin use."""
        items, total_items = await self.media_repository.list_all(page=page, limit=limit, search=search)

        total_pages = math.ceil(total_items / limit) if total_items > 0 else 1

        return PaginatedResponse(
            total_items=total_items,
            total_pages=total_pages,
            current_page=page,
            items=items
        )
