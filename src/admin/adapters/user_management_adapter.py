"""Adapters for routing admin façade calls to legacy user management services."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from src.auth.application.queries.auth_queries import AuthQueries
from src.auth.domain.user import User
from src.admin.application.services.admin_user_service import AdminUserService


@dataclass(slots=True)
class UserManagementAdapter:
    """Bridges the new admin façade with the legacy user management services."""

    auth_queries: AuthQueries
    admin_user_service: AdminUserService

    async def list_users(
        self,
        *,
        page: int,
        limit: int,
        search: Optional[str],
    ) -> list[User]:
        return await self.auth_queries.list_all(page=page, limit=limit, search=search)

    async def update_user_role(
        self,
        *,
        user_id: UUID,
        new_role: str,
        admin_user: User,
    ) -> User:
        return await self.admin_user_service.update_user_role(
            user_id=user_id,
            new_role=new_role,
            admin_user=admin_user,
        )

    async def delete_user(self, *, user_id: UUID, admin_user: User) -> None:
        await self.admin_user_service.delete_user(user_id, admin_user)

    async def activate_user(self, *, user_id: UUID, admin_user: User) -> User:
        return await self.admin_user_service.activate_user(user_id, admin_user)

    async def deactivate_user(self, *, user_id: UUID, admin_user: User) -> User:
        return await self.admin_user_service.deactivate_user(user_id, admin_user)
