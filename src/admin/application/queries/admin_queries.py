"""Query services that aggregate cross-module admin information."""

from datetime import datetime
from typing import Any, Dict
from uuid import UUID

from src.user_management.application.queries.auth_queries import AuthQueries
from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.domain.enums import MediaStatus


class AdminQueries:
    """Provides read-side operations tailored for administrative dashboards."""

    def __init__(self, auth_queries: AuthQueries, media_queries: MediaQueries) -> None:
        self._auth_queries = auth_queries
        self._media_queries = media_queries

    async def get_global_stats(self) -> Dict[str, Any]:
        """Aggregate high level statistics from multiple bounded contexts."""

        total_users = await self._auth_queries.count_all()
        active_users = await self._auth_queries.count_active()
        total_media = await self._media_queries.count_all()
        processing_media = await self._media_queries.count_by_status(MediaStatus.PROCESSING)
        failed_media = await self._media_queries.count_by_status(MediaStatus.FAILED)
        completed_media = await self._media_queries.count_by_status(MediaStatus.COMPLETED)

        success_rate = (completed_media / total_media * 100) if total_media else 0.0

        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_media": total_media,
            "processing_media": processing_media,
            "failed_media": failed_media,
            "completed_media": completed_media,
            "success_rate": success_rate,
        }

    async def get_user_activity_stats(self, user_id: UUID) -> Dict[str, Any]:
        """Return activity statistics for a specific user."""

        user = await self._auth_queries.get_by_id(user_id)
        if not user:
            raise ValueError(f"User with id {user_id} not found")

        total_media = await self._media_queries.count_by_user(user.id)
        processing_media = await self._media_queries.count_by_user_and_status(user.id, MediaStatus.PROCESSING)
        failed_media = await self._media_queries.count_by_user_and_status(user.id, MediaStatus.FAILED)
        completed_media = await self._media_queries.count_by_user_and_status(user.id, MediaStatus.COMPLETED)

        return {
            "user_id": str(user.id),
            "email": user.email,
            "total_media": total_media,
            "processing_media": processing_media,
            "failed_media": failed_media,
            "completed_media": completed_media,
            "is_active": user.is_active,
        }

    async def get_media_processing_stats(self) -> Dict[str, Any]:
        """Return detailed information about media processing throughput."""

        total = await self._media_queries.count_all()
        uploaded = await self._media_queries.count_by_status(MediaStatus.UPLOADED)
        processing = await self._media_queries.count_by_status(MediaStatus.PROCESSING)
        failed = await self._media_queries.count_by_status(MediaStatus.FAILED)
        completed = await self._media_queries.count_by_status(MediaStatus.COMPLETED)

        def percentage(part: int, whole: int) -> float:
            return (part / whole * 100) if whole else 0.0

        return {
            "total_media": total,
            "uploaded": uploaded,
            "processing": processing,
            "completed": completed,
            "failed": failed,
            "success_rate": percentage(completed, total),
            "failure_rate": percentage(failed, total),
            "processing_rate": percentage(processing, total),
        }

    async def get_system_health_status(self) -> Dict[str, Any]:
        """Return coarse health indicators for the platform."""

        total_failed = await self._media_queries.count_by_status(MediaStatus.FAILED)
        total_processing = await self._media_queries.count_by_status(MediaStatus.PROCESSING)
        total_users = await self._auth_queries.count_all()
        active_users = await self._auth_queries.count_active()

        health_status = "healthy"
        issues = []

        if total_failed > 10:
            health_status = "warning"
            issues.append(f"{total_failed} failed media items need attention")

        if total_processing > 50:
            health_status = "warning"
            issues.append(f"{total_processing} items in the processing queue")

        if total_users and (active_users / total_users) < 0.5:
            issues.append("Low user activity detected")

        return {
            "status": health_status,
            "total_users": total_users,
            "active_users": active_users,
            "failed_media": total_failed,
            "processing_media": total_processing,
            "issues": issues,
            "timestamp": datetime.utcnow().isoformat(),
        }