"""Adapter implementation for UserAdminPort."""
from __future__ import annotations

from uuid import UUID

from src.admin.application.ports import UserAdminPort
from src.user_management.application.services.user_service import UserService
from src.user_management.application.auth_queries import UserReadService
from src.user_management.application.dtos import (
    ListUsersQuery,
    GetUserQuery,
    DeleteUserCommand as UserDeleteCommand
)
from src.user_management.domain import User, UserRole


class UserManagementAdapter(UserAdminPort):
    """Wrapper around UserService and UserReadService to implement UserAdminPort."""

    def __init__(self, user_service: UserService, user_read_service: UserReadService):
        self._service = user_service
        self._read_service = user_read_service

    async def list_users(self, query: ListUsersQuery) -> dict:
        return await self._read_service.list_users(query)

    async def update_user_role(
        self,
        user_id: UUID,
        new_role: UserRole,
        admin_user: User,
    ) -> User:
        # Note: UserService.update_user could be used, but here we specifically map to role update
        from src.user_management.application.dtos import UpdateUserCommand
        cmd = UpdateUserCommand(user_id=user_id, role=new_role)
        return await self._service.update_user(cmd)

    async def delete_user(self, user_id: UUID, admin_user: User) -> None:
        await self._service.delete_user(UserDeleteCommand(user_id=user_id))

    async def activate_user(self, user_id: UUID, admin_user: User) -> User:
        return await self._service.activate_user(GetUserQuery(user_id=user_id))

    async def deactivate_user(self, user_id: UUID, admin_user: User) -> User:
        return await self._service.deactivate_user(GetUserQuery(user_id=user_id))