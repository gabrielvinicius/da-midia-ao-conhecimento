"""Service layer for admin operations acting as a facade over domain services."""
from __future__ import annotations

from dataclasses import dataclass

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

    # --- Stats & monitoring -------------------------------------------------
    async def get_system_stats(self, query: GetSystemStatsQuery) -> dict:
        return await self.admin_read_service.get_global_stats()

    async def get_system_health(self, query: GetSystemHealthQuery) -> dict:
        return await self.admin_read_service.get_system_health_status()

    async def get_media_processing_stats(
        self, query: GetMediaProcessingStatsQuery
    ) -> dict:
        return await self.admin_read_service.get_media_processing_stats()

    async def get_user_activity(self, query: GetUserActivityQuery) -> dict:
        return await self.admin_read_service.get_user_activity_stats(query.user_id)

    # --- Users --------------------------------------------------------------
    async def list_users(
        self,
        query: ListUsersQuery,
    ):
        return await self.user_adapter.list_users(query)

    async def update_user_role(
        self,
        command: UpdateUserRoleCommand,
    ) -> User:
        return await self.user_adapter.update_user_role(command)

    async def delete_user(self, command: DeleteUserCommand) -> None:
        await self.user_adapter.delete_user(command)

    async def activate_user(self, query: GetUserQuery) -> User:
        return await self.user_adapter.activate_user(query)

    async def deactivate_user(self, query: GetUserQuery) -> User:
        return await self.user_adapter.deactivate_user(query)

    # --- Media --------------------------------------------------------------
    async def list_media(self, query: ListMediaQuery):
        return await self.media_adapter.list_media(query)

    async def delete_media(self, command: DeleteMediaCommand) -> None:
        await self.media_adapter.delete_media(command)

    async def reprocess_media(self, command: ReprocessMediaCommand) -> None:
        await self.media_adapter.reprocess_media(command)

    async def bulk_reprocess_failed_media(
        self, command: BulkReprocessFailedMediaCommand
    ) -> int:
        return await self.media_adapter.bulk_reprocess_failed_media(command)
