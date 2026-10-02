from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol
from uuid import UUID

from src.admin.application.dtos import (
    BulkReprocessFailedMediaCommand,
    DeleteMediaCommand,
    DeleteUserCommand,
    ReprocessMediaCommand,
    UpdateUserRoleCommand,
)
from src.media_management.application.dtos import ListMediaQuery, PaginatedMedia
from src.user_management.application.dtos import GetUserQuery, ListUsersQuery
from src.user_management.domain import UserRole, User


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

    async def bulk_reprocess_failed_media(
        self, command: BulkReprocessFailedMediaCommand
    ) -> int: ...


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


# Repository ports to decouple Admin services from infra
class AdminUserRepositoryPort(Protocol):
    async def find_by_id(self, user_id: UUID) -> User | None: ...
    async def save(self, user: User) -> User: ...
    async def delete(self, user_id: UUID) -> bool: ...


class AdminMediaRepositoryPort(Protocol):
    async def get_by_id(self, media_id: UUID): ...
    async def update(self, media): ...
    async def delete(self, media_id: UUID): ...
    async def list_paginated(self, page: int, limit: int): ...
    async def list_by_status(self, status: Any) -> List[Any]: ...


class AdminMediaReadPort(Protocol):
    async def count_all(self) -> int: ...
    async def count_by_status(self, status, since=None) -> int: ...
    async def count_by_user(self, user_id: UUID) -> int: ...
    async def count_by_user_and_status(self, user_id: UUID, status) -> int: ...


class AdminUserReadPort(Protocol):
    async def count_all(self) -> int: ...
    async def count_active(self) -> int: ...
    async def get_user_by_id(self, query) -> object | None: ...


class AdminAuditPort(Protocol):
    async def log_admin_action(
        self,
        admin_user,
        action: str,
        target_type: str,
        target_id: UUID,
        details: dict | None = None,
    ) -> None: ...



__all__ = [
    "MediaAdminPort",
    "UserAdminPort",
    "AdminUserRepositoryPort",
    "AdminMediaRepositoryPort",
    "AdminMediaReadPort",
    "AdminUserReadPort",
    "AdminAuditPort",
]
