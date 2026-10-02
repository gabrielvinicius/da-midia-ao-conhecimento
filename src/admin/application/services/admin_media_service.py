"""Administrative media management services."""

from typing import List, Optional
from uuid import UUID

import structlog

from src.admin.application.ports import AdminMediaRepositoryPort
from src.admin.application.ports import AdminAuditPort
from src.admin.application.ports import MediaAdminPort
from src.media_management.application.dtos import (
    DeleteMediaCommand,
    ReprocessMediaCommand,
    ListMediaQuery,
    PaginatedMedia,
)
from src.media_management.domain import Media
from src.media_management.domain.enums import MediaStatus
from src.user_management.application.ports import PermissionServicePort
from src.user_management.domain import User, UserRole

logger = structlog.get_logger(__name__)


class AdminMediaService:
    """Admin-side operations over media with audit and permission checks."""

    def __init__(
        self,
        media_repository: AdminMediaRepositoryPort,
        permission_service: PermissionServicePort,
        audit_service: AdminAuditPort,
        media_service: MediaAdminPort,  # Updated type hint
    ) -> None:
        self.media_repository = media_repository
        self.permission_service = permission_service
        self.audit_service = audit_service
        self.media_service = media_service

    async def _dispatch_admin_delete(
        self,
        media_id: UUID,
        *,
        actor_id: Optional[str] = None,
        triggered_by: str = "admin",
    ) -> None:
        await self.media_service.delete_media(
            command=DeleteMediaCommand(media_id=media_id),
            user_id=UUID(actor_id) if actor_id else None,
            user_role=UserRole.ADMIN,
        )

    async def _dispatch_admin_reprocess(
        self,
        media_id: UUID,
        *,
        actor_id: Optional[str] = None,
        triggered_by: str = "admin",
    ) -> None:
        await self.media_service.reprocess_media(
            command=ReprocessMediaCommand(media_id=media_id),
            user_id=UUID(actor_id) if actor_id else None,
            user_role=UserRole.ADMIN,
        )

    async def _dispatch_bulk_reprocess(
        self,
        failed_media: List[Media],
        admin_user: User,
    ) -> int:
        reprocessed_count = 0
        for media_item in failed_media:
            try:
                await self.media_service.reprocess_media(
                    command=ReprocessMediaCommand(media_id=media_item.id),
                    user_id=admin_user.id,
                    user_role=UserRole.ADMIN,
                )
                reprocessed_count += 1
            except Exception as exc:  # pragma: no cover - best effort log
                logger.warning(
                    "admin.media.bulk_reprocess_failed_single_item",
                    media_id=str(media_item.id),
                    error=str(exc),
                )
        return reprocessed_count

    async def list_media(self, query: ListMediaQuery) -> PaginatedMedia:
        return await self.media_service.list_media(query)

    async def delete_media(self, media_id: UUID, admin_user: User) -> None:
        media = await self.media_repository.get_by_id(media_id)
        if not media:
            raise ValueError(f"Mídia com id {media_id} não foi encontrada")

        self.permission_service.require_admin(admin_user)

        await self._dispatch_admin_delete(media_id, actor_id=str(admin_user.id))

        await self.audit_service.log_admin_action(
            admin_user=admin_user,
            action="delete_media",
            target_type="media",
            target_id=media_id,
            details={"media_status": media.status.value},
        )

    async def reprocess_media(self, media_id: UUID, admin_user: User) -> None:
        media = await self.media_repository.get_by_id(media_id)
        if not media:
            raise ValueError(f"Mídia com id {media_id} não foi encontrada")

        self.permission_service.require_admin(admin_user)

        # A regra de quando reprocessar é do domínio da mídia.
        media.ensure_can_be_reprocessed()

        await self._dispatch_admin_reprocess(
            media_id, actor_id=str(admin_user.id), triggered_by="admin"
        )

        await self.audit_service.log_admin_action(
            admin_user=admin_user,
            action="reprocess_media",
            target_type="media",
            target_id=media_id,
            details={"media_status": media.status.value},
        )

    async def bulk_reprocess_failed_media(self, admin_user: User) -> int:
        failed_media = await self.get_media_by_status(MediaStatus.FAILED)
        reprocessed_count = await self._dispatch_bulk_reprocess(
            failed_media, admin_user
        )

        await self.audit_service.log_admin_action(
            admin_user=admin_user,
            action="bulk_reprocess_media",
            target_type="media",
            target_id=UUID(int=0),
            details={"reprocessed_count": reprocessed_count},
        )

        return reprocessed_count

    async def get_media_by_status(self, status: MediaStatus) -> List[Media]:
        return await self.media_repository.list_by_status(status)

    async def force_media_status(
        self,
        media_id: UUID,
        new_status: MediaStatus,
        admin_user: User,
        reason: Optional[str] = None,
    ) -> None:
        media = await self.media_repository.get_by_id(media_id)
        if not media:
            raise ValueError(f"Media with id {media_id} not found")

        self.permission_service.require_admin(admin_user)

        media.override_status(new_status)
        await self.media_repository.update(media)

        await self.audit_service.log_admin_action(
            admin_user=admin_user,
            action="force_media_status",
            target_type="media",
            target_id=media_id,
            details={"new_status": new_status.value, "reason": reason},
        )