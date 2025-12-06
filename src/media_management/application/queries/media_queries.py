from typing import Protocol, Optional, List, Dict, Any
from uuid import UUID

from src.media_management.domain.media import Media
from src.media_management.application.queries.dto import (
    GetMediaQuery,
    ListMediaQuery,
    GetMediaStatisticsQuery,
)

class MediaQueries(Protocol):
    """Interface for media query operations."""

    async def get_by_id(self, media_id: UUID) -> Optional[Media]:
        """Retrieve a media item by its ID."""
        ...

    async def list_paginated(
        self,
        page: int = 1,
        limit: int = 10,
        user_id: Optional[UUID] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[Media]:
        """List media items with pagination and filters."""
        ...

    async def get_media(self, query: GetMediaQuery) -> Optional[Media]:
        """Retrieves a single media entity."""
        ...

    async def list_media(self, query: ListMediaQuery) -> List[Media]:
        """Lists media entities with pagination and filtering."""
        ...

    async def get_media_statistics(self, query: GetMediaStatisticsQuery) -> Dict[str, Any]:
        """Returns statistics about media entities."""
        ...

