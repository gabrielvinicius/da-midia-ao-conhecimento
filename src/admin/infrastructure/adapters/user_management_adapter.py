"""Adapters que conectam a fachada admin aos serviços de user_management."""
from __future__ import annotations

import math
from dataclasses import dataclass
from uuid import UUID

from src.admin.application.dtos import DeleteUserCommand, UpdateUserRoleCommand
from src.admin.application.ports import UserAdminPort
from src.admin.application.services.admin_user_service import AdminUserService
from src.user_management.application.auth_queries import UserReadService
from src.user_management.application.dtos import GetUserQuery, ListUsersQuery
from src.user_management.domain import User, UserRole


@dataclass(slots=True)
class UserManagementAdapter(UserAdminPort):
    """Bridge da fachada admin para os serviços de user_management."""

    auth_queries: UserReadService
    admin_user_service: AdminUserService

    async def list_users(self, query: ListUsersQuery) -> list[User]:
        items = await self.auth_queries.list_all(
            page=query.page,
            limit=query.limit,
            search=query.search,
        )
        total_items = await self.auth_queries.count_filtered(search=query.search)
        total_pages = math.ceil(total_items / query.limit) if query.limit else 1
        return {
            "items": items,
            "total_items": total_items,
            "total_pages": total_pages,
            "current_page": query.page,
        }

    async def update_user_role(self, command: UpdateUserRoleCommand) -> User:
        admin = await self._resolve_admin(command.admin_user_id)
        return await self.admin_user_service.update_user_role(
            user_id=command.user_id,
            new_role=command.new_role,
            admin_user=admin,
        )

    async def delete_user(self, command: DeleteUserCommand) -> None:
        admin = await self._resolve_admin(command.admin_user_id)
        await self.admin_user_service.delete_user(command.user_id, admin)

    async def activate_user(self, query: GetUserQuery) -> User:
        admin = await self._resolve_admin(query.admin_user_id)
        return await self.admin_user_service.activate_user(query.user_id, admin)

    async def deactivate_user(self, query: GetUserQuery) -> User:
        admin = await self._resolve_admin(query.admin_user_id)
        return await self.admin_user_service.deactivate_user(query.user_id, admin)

    async def _resolve_admin(self, admin_id: UUID) -> User:
        if not admin_id:
            raise PermissionError(
                "admin_user_id é obrigatório para operações administrativas."
            )
        query = GetUserQuery(user_id=admin_id, admin_user_id=admin_id)
        if hasattr(self.auth_queries, "get_user_by_id"):
            found = await self.auth_queries.get_user_by_id(query)
            if (
                found
                and getattr(found.role, "value", "").upper() == UserRole.ADMIN.value
            ):
                return found
        raise PermissionError("Admin não encontrado ou sem permissão.")
