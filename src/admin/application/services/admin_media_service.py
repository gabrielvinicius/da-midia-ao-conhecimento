"""Ações administrativas sobre mídias, com permissão e auditoria."""

from dataclasses import dataclass
from uuid import UUID

import structlog

from src.admin.application.ports import AdminAuditPort, MediaAdminPort
from src.media_management.application.dtos import ListMediaQuery, PaginatedMedia
from src.shared.domain.errors import NotFoundError
from src.user_management.application.ports import PermissionServicePort
from src.user_management.domain import User

logger = structlog.get_logger(__name__)

# Teto de um pedido de reprocessamento em lote. Antes, todas as mídias com
# falha eram carregadas e reprocessadas dentro de um único pedido HTTP.
BULK_REPROCESS_MAX = 200


@dataclass(frozen=True)
class BulkReprocessResult:
    reprocessed: int
    failed: int
    more_pending: bool  # ainda há mídias com falha além deste lote


class AdminMediaService:
    def __init__(
        self,
        media: MediaAdminPort,
        permission_service: PermissionServicePort,
        audit_service: AdminAuditPort,
    ) -> None:
        self._media = media
        self.permission_service = permission_service
        self.audit_service = audit_service

    async def list_media(self, query: ListMediaQuery) -> PaginatedMedia:
        return await self._media.list_media(query)

    async def delete_media(self, media_id: UUID, admin_user: User) -> None:
        self.permission_service.require_admin(admin_user)
        status = await self._existing_status(media_id)
        await self._media.delete_media(media_id, actor_id=admin_user.id)
        await self._audit(admin_user, "delete_media", media_id, {"media_status": status})

    async def reprocess_media(self, media_id: UUID, admin_user: User) -> None:
        """A regra de quando reprocessar é do módulo de mídias, que a aplica."""
        self.permission_service.require_admin(admin_user)
        status = await self._existing_status(media_id)
        await self._media.reprocess_media(media_id, actor_id=admin_user.id)
        await self._audit(admin_user, "reprocess_media", media_id, {"media_status": status})

    async def bulk_reprocess_failed_media(self, admin_user: User, limit: int) -> BulkReprocessResult:
        """Reprocessa até ``limit`` mídias com falha, das mais antigas para as
        mais novas. As reprocessadas saem do estado de falha, então o próximo
        pedido pega o lote seguinte."""
        self.permission_service.require_admin(admin_user)
        limit = max(1, min(limit, BULK_REPROCESS_MAX))
        ids = await self._media.failed_media_ids(limit + 1)
        batch = ids[:limit]
        reprocessed = 0
        for media_id in batch:
            try:
                await self._media.reprocess_media(media_id, actor_id=admin_user.id)
                reprocessed += 1
            except Exception as exc:  # uma mídia não impede as outras
                logger.warning("admin.media.bulk_reprocess_item_failed", media_id=str(media_id), error=str(exc))
        result = BulkReprocessResult(
            reprocessed=reprocessed, failed=len(batch) - reprocessed, more_pending=len(ids) > limit
        )
        await self._audit(
            admin_user, "bulk_reprocess_media", UUID(int=0),
            {"reprocessed_count": result.reprocessed, "failed_count": result.failed},
        )
        return result

    async def _existing_status(self, media_id: UUID) -> str:
        status = await self._media.status_of(media_id)
        if status is None:
            raise NotFoundError("Mídia não encontrada")
        return status

    async def _audit(self, admin_user: User, action: str, media_id: UUID, details: dict) -> None:
        await self.audit_service.log_admin_action(
            admin_user=admin_user, action=action, target_type="media", target_id=media_id, details=details
        )
