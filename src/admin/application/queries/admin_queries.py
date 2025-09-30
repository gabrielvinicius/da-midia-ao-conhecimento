# src/admin/application/queries/admin_queries.py
from src.auth.application.queries.auth_queries import AuthQueries
from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.domain.media import MediaStatus

class AdminQueries:
    """Handles complex, cross-module queries for the admin panel."""
    def __init__(self, auth_queries: AuthQueries, media_queries: MediaQueries):
        self.auth_queries = auth_queries
        self.media_queries = media_queries

    async def get_global_stats(self) -> dict:
        """Aggregates statistics from multiple domains."""
        total_users = await self.auth_queries.count_all()
        total_media = await self.media_queries.count_all()
        processing_media = await self.media_queries.count_by_status(MediaStatus.PROCESSING)

        return {
            "total_users": total_users,
            "total_media": total_media,
            "processing_media": processing_media,
        }
