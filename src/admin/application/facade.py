"""Admin façade that orchestrates legacy services behind a unified interface."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from src.admin.adapters import MediaManagementAdapter, UserManagementAdapter
from src.admin.application.queries.admin_queries import AdminQueries
from src.admin.application.services.admin_audit_service import AdminAuditService
from src.admin.application.services.admin_media_service import AdminMediaService
from src.admin.application.services.admin_user_service import AdminUserService
from src.user_management.application.queries.auth_queries import AuthQueries
from src.user_management.domain.user import User
from src.media_management.application.queries.media_queries import MediaQueries


ADMIN_FACADE_ENV_FLAG = "ADMIN_FACADE_ENABLED"


def is_admin_facade_enabled() -> bool:
    """Decides whether the façade should be used or bypassed."""

    raw_value = os.getenv(ADMIN_FACADE_ENV_FLAG, "true")
    return raw_value.lower() not in {"0", "false", "no", "off"}


@dataclass(slots=True)
class AdminFacade:
    """High-level orchestrator delegating to adapters or legacy services."""

    admin_queries: AdminQueries
    audit_service: AdminAuditService
    auth_queries: AuthQueries
    media_queries: MediaQueries
    admin_user_service: AdminUserService
    admin_media_service: AdminMediaService
    user_adapter: UserManagementAdapter
    media_adapter: MediaManagementAdapter
    enabled: bool = True

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
        if self.enabled:
            return await self.user_adapter.list_users(page=page, limit=limit, search=search)
        return await self.auth_queries.list_all(page=page, limit=limit, search=search)

    async def update_user_role(
        self,
        *,
        user_id: UUID,
        new_role: str,
        admin_user: User,
    ) -> User:
        if self.enabled:
            return await self.user_adapter.update_user_role(
                user_id=user_id,
                new_role=new_role,
                admin_user=admin_user,
            )
        return await self.admin_user_service.update_user_role(
            user_id=user_id,
            new_role=new_role,
            admin_user=admin_user,
        )

    async def delete_user(self, *, user_id: UUID, admin_user: User) -> None:
        if self.enabled:
            await self.user_adapter.delete_user(user_id=user_id, admin_user=admin_user)
            return
        await self.admin_user_service.delete_user(user_id, admin_user)

    async def activate_user(self, *, user_id: UUID, admin_user: User) -> User:
        if self.enabled:
            return await self.user_adapter.activate_user(user_id=user_id, admin_user=admin_user)
        return await self.admin_user_service.activate_user(user_id, admin_user)

    async def deactivate_user(self, *, user_id: UUID, admin_user: User) -> User:
        if self.enabled:
            return await self.user_adapter.deactivate_user(user_id=user_id, admin_user=admin_user)
        return await self.admin_user_service.deactivate_user(user_id, admin_user)

    # --- Media --------------------------------------------------------------
    async def list_media(
        self,
        *,
        page: int,
        limit: int,
        search: Optional[str],
    ):
        if self.enabled:
            return await self.media_adapter.list_media(page=page, limit=limit, search=search)
        return await self.media_queries.list_all(page=page, limit=limit, search=search)

    async def delete_media(self, *, media_id: UUID, admin_user: User) -> None:
        if self.enabled:
            await self.media_adapter.delete_media(media_id=media_id, admin_user=admin_user)
            return
        await self.admin_media_service.delete_media(media_id, admin_user)

    async def reprocess_media(self, *, media_id: UUID, admin_user: User) -> None:
        if self.enabled:
            await self.media_adapter.reprocess_media(media_id=media_id, admin_user=admin_user)
            return
        await self.admin_media_service.reprocess_media(media_id, admin_user)

    async def bulk_reprocess_failed_media(self, *, admin_user: User) -> int:
        if self.enabled:
            return await self.media_adapter.bulk_reprocess_failed_media(admin_user=admin_user)
        return await self.admin_media_service.bulk_reprocess_failed_media(admin_user)

    async def cleanup_orphaned_files(self, *, admin_user: User) -> int:
        if self.enabled:
            return await self.media_adapter.cleanup_orphaned_files(admin_user=admin_user)
        return await self.admin_media_service.cleanup_orphaned_files(admin_user)


__all__ = [
    "AdminFacade",
    "ADMIN_FACADE_ENV_FLAG",
    "is_admin_facade_enabled",
]
