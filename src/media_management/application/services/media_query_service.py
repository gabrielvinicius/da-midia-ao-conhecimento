"""Service encapsulating read-only media operations."""

from typing import Dict, Any, List, Optional
from uuid import UUID

from src.user_management.domain.user import UserRole
from src.media_management.application.policies import MediaAccessPolicy
from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.domain.enums import MediaStatus
from src.media_management.domain.media import Media


class MediaQueryService:
    """Provides query operations with integrated authorization checks."""

    def __init__(self, media_queries: MediaQueries, access_policy: MediaAccessPolicy) -> None:
        self._media_queries = media_queries
        self._access_policy = access_policy

    async def list_media_for_user(
        self,
        user_id: UUID,
        status: Optional[MediaStatus] = None,
        page: int = 1,
        limit: int = 10,
        search: Optional[str] = None,
    ) -> List[Media]:
        """List media entries scoped to the provided user."""

        return await self._media_queries.list_all(
            user_id=user_id,
            status=status,
            page=page,
            limit=limit,
            search=search,
        )

    async def get_media_for_user(
        self, media_id: UUID, user_id: UUID, user_role: Optional[UserRole] = None
    ) -> Media:
        """Retrieve a media entry ensuring the user can access it."""

        media = await self._media_queries.get_by_id(media_id)
        if not media:
            raise ValueError(f"Media {media_id} not found")

        self._access_policy.ensure_can_access(media, user_id, user_role)
        return media

    async def get_media_statistics(self, user_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Aggregate statistics either globally or for a specific user."""

        if user_id:
            total = await self._media_queries.count_by_user(user_id)
            by_status: Dict[str, int] = {}
            for status in MediaStatus:
                count = await self._media_queries.count_by_user_and_status(user_id, status)
                by_status[status.value] = count
        else:
            total = await self._media_queries.count_all()
            by_status = {}
            for status in MediaStatus:
                count = await self._media_queries.count_by_status(status)
                by_status[status.value] = count

        return {"total": total, "by_status": by_status}
