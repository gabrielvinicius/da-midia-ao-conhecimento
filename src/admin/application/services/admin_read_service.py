"""Query services that aggregate cross-module admin information."""

from typing import Any, Dict
from uuid import UUID

from src.admin.application.ports import AdminMediaReadPort, AdminUserReadPort
from src.media_management.domain.enums import MediaStatus
from src.shared.domain.time.clock import utcnow
from src.user_management.application.dtos import GetUserQuery


class AdminReadService:
    """Provides read-side operations tailored for administrative dashboards."""

    def __init__(
        self,
        user_read_port: AdminUserReadPort,
        media_read_port: AdminMediaReadPort,
    ) -> None:
        self._user_read_service = user_read_port
        self._media_read_service = media_read_port

    async def get_global_stats(self) -> Dict[str, Any]:
        """Aggregate high level statistics from multiple bounded contexts."""
        total_users = await self._user_read_service.count_all()
        active_users = await self._user_read_service.count_active()
        total_media = await self._media_read_service.count_all()
        processing_media = await self._media_read_service.count_by_status(
            MediaStatus.PROCESSING
        )
        failed_media = await self._media_read_service.count_by_status(
            MediaStatus.FAILED
        )
        completed_media = await self._media_read_service.count_by_status(
            MediaStatus.COMPLETED
        )

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
        user = await self._user_read_service.get_user_by_id(
            GetUserQuery(user_id=user_id)
        )
        if not user:
            raise ValueError(f"Usuário com id {user_id} não foi encontrado")

        total_media = await self._media_read_service.count_by_user(user.id)
        processing_media = await self._media_read_service.count_by_user_and_status(
            user.id, MediaStatus.PROCESSING
        )
        failed_media = await self._media_read_service.count_by_user_and_status(
            user.id, MediaStatus.FAILED
        )
        completed_media = await self._media_read_service.count_by_user_and_status(
            user.id, MediaStatus.COMPLETED
        )

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
        total = await self._media_read_service.count_all()
        uploaded = await self._media_read_service.count_by_status(MediaStatus.UPLOADED)
        processing = await self._media_read_service.count_by_status(
            MediaStatus.PROCESSING
        )
        failed = await self._media_read_service.count_by_status(MediaStatus.FAILED)
        completed = await self._media_read_service.count_by_status(
            MediaStatus.COMPLETED
        )

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
        total_failed = await self._media_read_service.count_by_status(
            MediaStatus.FAILED
        )
        total_processing = await self._media_read_service.count_by_status(
            MediaStatus.PROCESSING
        )
        total_users = await self._user_read_service.count_all()
        active_users = await self._user_read_service.count_active()

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
            "timestamp": utcnow().isoformat(),
        }

# Backward compatibility
