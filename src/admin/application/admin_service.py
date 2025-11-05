"""Service layer for admin operations acting as a facade over domain services."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from src.admin.application.queries.admin_queries import AdminQueries
from src.admin.application.services.admin_audit_service import AdminAuditService
from src.admin.application.services.admin_media_service import AdminMediaService
from src.admin.application.services.admin_user_service import AdminUserService
from src.media_management.application.queries.media_queries import MediaQueries
from src.user_management.application.queries.auth_queries import AuthQueries
from src.user_management.domain.user import User

if TYPE_CHECKING:
    from src.admin.adapters import MediaManagementAdapter, UserManagementAdapter


@dataclass(slots=True)
class AdminService:
    """High-level orchestrator delegating admin actions to domain services."""

    admin_queries: AdminQueries
    audit_service: AdminAuditService
    auth_queries: AuthQueries
    media_queries: MediaQueries
    admin_user_service: AdminUserService
    admin_media_service: AdminMediaService
    user_adapter: "UserManagementAdapter"
    media_adapter: "MediaManagementAdapter"

    # --- Stats & monitoring -------------------------------------------------
    async def get_system_stats(self) -> dict:
        return await self.admin_queries.get_global_stats()

    async def get_system_health(self) -> dict:
        return await self.admin_queries.get_system_health_status()

    async def get_media_processing_stats(self) -> dict:
        return await self.admin_queries.get_media_processing_stats()

    async def get_user_activity(self, *, user_id: UUID) -> dict:
        return await self.admin_queries.get_user_activity_stats(user_id)

    # --- Users --------------------------------------------------------------
    async def list_users(
        self,
        *,
        page: int,
        limit: int,
        search: Optional[str],
    ):
        return await self.user_adapter.list_users(page=page, limit=limit, search=search)

    async def update_user_role(
        self,
        *,
        user_id: UUID,
        new_role: str,
        admin_user: User,
    ) -> User:
        return await self.user_adapter.update_user_role(
            user_id=user_id,
            new_role=new_role,
            admin_user=admin_user,
        )

    async def delete_user(self, *, user_id: UUID, admin_user: User) -> None:
        await self.user_adapter.delete_user(user_id=user_id, admin_user=admin_user)

    async def activate_user(self, *, user_id: UUID, admin_user: User) -> User:
        return await self.user_adapter.activate_user(user_id=user_id, admin_user=admin_user)

    async def deactivate_user(self, *, user_id: UUID, admin_user: User) -> User:
        return await self.user_adapter.deactivate_user(user_id=user_id, admin_user=admin_user)

    # --- Media --------------------------------------------------------------
    async def list_media(
        self,
        *,
        page: int,
        limit: int,
        search: Optional[str],
    ):
        return await self.media_adapter.list_media(page=page, limit=limit, search=search)

    async def delete_media(self, *, media_id: UUID, admin_user: User) -> None:
        await self.media_adapter.delete_media(media_id=media_id, admin_user=admin_user)

    async def reprocess_media(self, *, media_id: UUID, admin_user: User) -> None:
        await self.media_adapter.reprocess_media(media_id=media_id, admin_user=admin_user)

    async def bulk_reprocess_failed_media(self, *, admin_user: User) -> int:
        return await self.media_adapter.bulk_reprocess_failed_media(admin_user=admin_user)

    async def cleanup_orphaned_files(self, *, admin_user: User) -> int:
        return await self.media_adapter.cleanup_orphaned_files(admin_user=admin_user)


__all__ = [
    "AdminService",
]
