"""External ports required by the Admin module."""
from __future__ import annotations

from typing import List, Optional, Protocol
from uuid import UUID

from src.media_management.application.dtos import (
    DeleteMediaCommand,
    ListMediaQuery,
    PaginatedMedia,
    ReprocessMediaCommand,
)
from src.user_management.domain import User, UserRole


class MediaAdminPort(Protocol):
    """Port to interact with the Media Management context."""

    async def delete_media(
        self,
        command: DeleteMediaCommand,
        user_id: Optional[UUID] = None,
        user_role: Optional[UserRole] = None,
    ) -> None: ...

    async def reprocess_media(
        self,
        command: ReprocessMediaCommand,
        user_id: Optional[UUID] = None,
        user_role: Optional[UserRole] = None,
    ) -> None: ...

    async def list_media(self, query: ListMediaQuery) -> PaginatedMedia: ...


from src.user_management.application.dtos import (
    GetUserQuery,
    ListUsersQuery,
    UpdateUserCommand,
    DeleteUserCommand as UserDeleteCommand
)

class UserAdminPort(Protocol):
    """Port to interact with the User Management context."""
    async def list_users(self, query: ListUsersQuery) -> dict: ...

    async def update_user_role(
        self,
        user_id: UUID,
        new_role: UserRole,
        admin_user: User,
    ) -> User: ...

    async def delete_user(self, user_id: UUID, admin_user: User) -> None: ...

    async def activate_user(self, user_id: UUID, admin_user: User) -> User: ...

    async def deactivate_user(self, user_id: UUID, admin_user: User) -> User: ...


