"""Service layer for admin operations acting as a facade over domain services."""
from __future__ import annotations

from typing import Any, Optional

from src.shared.application.ports import ProcessingStatsPort

from dataclasses import dataclass
from uuid import UUID

from src.admin.application.ports import MediaAdminPort, UserAdminPort
from src.media_management.application.dtos import (
    ListMediaQuery,
)
from src.user_management.application.dtos import GetUserQuery, ListUsersQuery
from src.user_management.domain import User

from ..dtos import (
    BulkReprocessFailedMediaCommand,
    DeleteMediaCommand,
    DeleteUserCommand,
    GetMediaProcessingStatsQuery,
    GetSystemHealthQuery,
    GetSystemStatsQuery,
    GetUserActivityQuery,
    ReprocessMediaCommand,
    UpdateUserRoleCommand,
)
from .admin_audit_service import AdminAuditService
from .admin_media_service import AdminMediaService
from .admin_read_service import AdminReadService
from .admin_user_service import AdminUserService


@dataclass(slots=True)
class AdminService:
    """High-level orchestrator delegating admin actions to domain services."""

    admin_read_service: AdminReadService
    audit_service: AdminAuditService
    admin_user_service: AdminUserService
    admin_media_service: AdminMediaService
    user_adapter: UserAdminPort
    media_adapter: MediaAdminPort
    processing_stats: Optional[ProcessingStatsPort] = None

    # --- Stats & monitoring -------------------------------------------------
    async def get_system_stats(self, query: GetSystemStatsQuery) -> dict:
        return await self.admin_read_service.get_global_stats()

    async def get_system_health(self, query: GetSystemHealthQuery) -> dict:
        return await self.admin_read_service.get_system_health_status()

    async def get_processing_times(self, days: Optional[int] = None) -> dict:
        """Durações registradas de transcrição e de cada etapa da análise."""
        items = await self.processing_stats.summarize(days) if self.processing_stats else []
        return {"days": days, "items": items}

    async def get_media_processing_stats(
        self, query: GetMediaProcessingStatsQuery
    ) -> dict:
        return await self.admin_read_service.get_media_processing_stats()

    async def get_user_activity(self, query: GetUserActivityQuery) -> dict:
        return await self.admin_read_service.get_user_activity_stats(query.user_id)

    # --- Users --------------------------------------------------------------
    async def list_users(self, query: ListUsersQuery):
        return await self.admin_user_service.list_users(query)

    async def update_user_role(
        self,
        user_id: UUID,
        new_role: Any,
        admin_user: User,
    ) -> User:
        return await self.admin_user_service.update_user_role(
            user_id=user_id,
            new_role=new_role,
            admin_user=admin_user
        )

    async def delete_user(self, user_id: UUID, admin_user: User) -> None:
        await self.admin_user_service.delete_user(
            user_id=user_id,
            admin_user=admin_user
        )

    async def activate_user(self, user_id: UUID, admin_user: User) -> User:
        return await self.admin_user_service.activate_user(user_id, admin_user)

    async def deactivate_user(self, user_id: UUID, admin_user: User) -> User:
        return await self.admin_user_service.deactivate_user(user_id, admin_user)

    # --- Media --------------------------------------------------------------
    async def list_media(self, query: ListMediaQuery):
        return await self.admin_media_service.list_media(query)

    async def delete_media(self, media_id: UUID, admin_user: User) -> None:
        await self.admin_media_service.delete_media(
            media_id=media_id,
            admin_user=admin_user
        )

    async def reprocess_media(self, media_id: UUID, admin_user: User) -> None:
        await self.admin_media_service.reprocess_media(
            media_id=media_id,
            admin_user=admin_user
        )

    async def bulk_reprocess_failed_media(self, admin_user: User) -> int:
        return await self.admin_media_service.bulk_reprocess_failed_media(admin_user)