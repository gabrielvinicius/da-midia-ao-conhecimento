"""Service layer for admin operations acting as a facade over domain services."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from src.admin.application.queries.admin_queries import AdminQueries # Alias for AdminReadService
from src.admin.application.services.admin_audit_service import AdminAuditService
from src.admin.application.services.admin_media_service import AdminMediaService
from src.admin.application.services.admin_user_service import AdminUserService
from src.media_management.application.queries.media_queries import MediaQueries # Alias for MediaReadService
from src.user_management.application.auth_queries import AuthQueries
from src.user_management.domain.user import User

from src.admin.application.commands.dto import (
    BulkReprocessFailedMediaCommand,
    DeleteMediaCommand,
    DeleteUserCommand,
    ReprocessMediaCommand,
    UpdateUserRoleCommand,
)
from src.admin.application.queries.dto import (
    GetMediaProcessingStatsQuery,
    GetSystemHealthQuery,
    GetSystemStatsQuery,
    GetUserActivityQuery,
)
from src.media_management.application.commands.dto import (
    CleanupOrphanedFilesCommand,
)
from src.media_management.application.queries.dto import (
    ListMediaQuery,
)
from src.user_management.application.queries.dto import (
    GetUserQuery,
    ListUsersQuery,
)


if TYPE_CHECKING:
    from src.admin.adapters import MediaManagementAdapter, UserManagementAdapter


@dataclass(slots=True)
class AdminService:
    """High-level orchestrator delegating admin actions to domain services."""

    admin_queries: AdminQueries
    audit_service: AdminAuditService
    auth_queries: AuthQueries
    media_queries: MediaQueries # This is a legacy query service
    admin_user_service: AdminUserService
    admin_media_service: AdminMediaService
    user_adapter: "UserManagementAdapter"
    media_adapter: "MediaManagementAdapter"

    # --- Stats & monitoring -------------------------------------------------
    async def get_system_stats(self, query: GetSystemStatsQuery) -> dict:
        return await self.admin_queries.get_global_stats()

    async def get_system_health(self, query: GetSystemHealthQuery) -> dict:
        return await self.admin_queries.get_system_health_status()

    async def get_media_processing_stats(self, query: GetMediaProcessingStatsQuery) -> dict:
        return await self.admin_queries.get_media_processing_stats()

    async def get_user_activity(self, query: GetUserActivityQuery) -> dict:
        return await self.admin_queries.get_user_activity_stats(query.user_id) # admin_queries expects raw UUID

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
        # UserAdapter expects admin_user too.
        # This will require changes in UserManagementAdapter.activate_user
        # For now, will pass through admin_user for compatibility.
        return await self.user_adapter.activate_user(query)

    async def deactivate_user(self, query: GetUserQuery) -> User:
        # Same as activate_user
        return await self.user_adapter.deactivate_user(query)

    # --- Media --------------------------------------------------------------
    async def list_media(
        self,
        query: ListMediaQuery,
    ):
        return await self.media_adapter.list_media(query)

    async def delete_media(self, command: DeleteMediaCommand) -> None:
        await self.media_adapter.delete_media(command)

    async def reprocess_media(self, command: ReprocessMediaCommand) -> None:
        await self.media_adapter.reprocess_media(command)

    async def bulk_reprocess_failed_media(self, command: BulkReprocessFailedMediaCommand) -> int:
        return await self.media_adapter.bulk_reprocess_failed_media(command)

    async def cleanup_orphaned_files(self, command: CleanupOrphanedFilesCommand) -> int:
        return await self.media_adapter.cleanup_orphaned_files(command)


__all__ = [
    "AdminService",
]