"""Query services that aggregate cross-module admin information."""

from datetime import timedelta
from typing import Any, Dict
from uuid import UUID

from src.shared.domain.errors import NotFoundError
from src.admin.application.ports import AdminMediaReadPort, AdminUserReadPort
from src.media_management.domain.enums import IN_PROGRESS_STATUSES, MediaStatus
from src.shared.domain.time.clock import utcnow
from src.user_management.application.dtos import GetUserQuery


class AdminReadService:
    """Provides read-side operations tailored for administrative dashboards."""

    def __init__(
        self,
        user_read_port: AdminUserReadPort,
        media_read_port: AdminMediaReadPort,
        *,
        failure_window_hours: int = 24,
        failed_alert: int = 5,
        queue_alert: int = 20,
    ) -> None:
        self._user_read_service = user_read_port
        self._media_read_service = media_read_port
        self.failure_window_hours = failure_window_hours
        self.failed_alert = failed_alert
        self.queue_alert = queue_alert

    async def _count_in_progress(self) -> int:
        """Em processamento ou em análise: as duas etapas ocupam os workers."""
        return sum([await self._media_read_service.count_by_status(s) for s in IN_PROGRESS_STATUSES])

    async def _count_user_in_progress(self, user_id: UUID) -> int:
        return sum(
            [await self._media_read_service.count_by_user_and_status(user_id, s) for s in IN_PROGRESS_STATUSES]
        )

    async def get_global_stats(self) -> Dict[str, Any]:
        """Aggregate high level statistics from multiple bounded contexts."""
        total_users = await self._user_read_service.count_all()
        active_users = await self._user_read_service.count_active()
        total_media = await self._media_read_service.count_all()
        processing_media = await self._count_in_progress()
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
            raise NotFoundError("Usuário não encontrado")

        total_media = await self._media_read_service.count_by_user(user.id)
        processing_media = await self._count_user_in_progress(user.id)
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
        processing = await self._count_in_progress()
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
        """Alertas do painel, em português e sobre o que pede ação agora.

        Antes, o total de falhas desde sempre ligava o alerta para sempre
        (bastavam 11), e "baixa atividade" contava contas desativadas, não uso.
        Agora contam as falhas recentes e o tamanho da fila; os limites são
        parâmetros do serviço.
        """
        since = utcnow() - timedelta(hours=self.failure_window_hours)
        recent_failures = await self._media_read_service.count_by_status(MediaStatus.FAILED, since=since)
        processing = await self._count_in_progress()
        waiting = await self._media_read_service.count_by_status(MediaStatus.UPLOADED)

        issues = []
        if recent_failures >= self.failed_alert:
            issues.append(
                f"{recent_failures} mídias falharam nas últimas {self.failure_window_hours} horas: "
                "veja o motivo na lista de mídias."
            )
        if processing + waiting >= self.queue_alert:
            issues.append(f"{processing + waiting} mídias aguardando ou em processamento: a fila está longa.")
        return {
            "status": "warning" if issues else "healthy",
            "total_users": await self._user_read_service.count_all(),
            "active_users": await self._user_read_service.count_active(),
            "failed_media": recent_failures,
            "failure_window_hours": self.failure_window_hours,
            "processing_media": processing,
            "waiting_media": waiting,
            "issues": issues,
            "timestamp": utcnow().isoformat(),
        }


# Backward compatibility
