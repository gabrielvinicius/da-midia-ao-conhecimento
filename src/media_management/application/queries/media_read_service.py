"""Media Queries Service.

Provides read-only access to Media statistics and data.
"""

from uuid import UUID

from src.media_management.infrastructure.repositories import MediaRepository
from src.shared.domain.enums import MediaStatus


class MediaReadService:
    """Read-side facade for Media data."""

    def __init__(self, media_repository: MediaRepository) -> None:
        self.repository = media_repository

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

# Backward compatibility
MediaQueries = MediaReadService