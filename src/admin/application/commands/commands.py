"""
Admin Commands - Pure data classes following Command Pattern
"""
from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class DeleteMediaCommand:
    """Command to delete media by admin"""
    media_id: UUID
    admin_user_id: Optional[UUID] = None
    reason: Optional[str] = None


@dataclass(frozen=True)
class DeleteUserCommand:
    """Command to delete user by admin"""
    user_id: UUID
    admin_user_id: UUID
    reason: Optional[str] = None


@dataclass(frozen=True)
class ReprocessMediaCommand:
    """Command to reprocess media by admin"""
    media_id: UUID
    admin_user_id: UUID
    force: bool = False


@dataclass(frozen=True)
class UpdateUserRoleCommand:
    """Command to update user role by admin"""
    user_id: UUID
    new_role: str
    admin_user_id: UUID
    reason: Optional[str] = None
