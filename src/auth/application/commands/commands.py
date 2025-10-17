"""
Auth Commands - Pure data classes following Command Pattern
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from uuid import UUID


@dataclass(frozen=True)
class AuthenticateUserCommand:
    """Command to authenticate user"""
    email: str
    password: str
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None


@dataclass(frozen=True)
class CreateUserCommand:
    """Command to create new user"""
    email: str
    password: str
    username: Optional[str] = None
    role: Optional[str] = "user"


@dataclass(frozen=True)
class ChangePasswordCommand:
    """Command to change user password"""
    user_id: UUID
    old_password: str
    new_password: str


@dataclass(frozen=True)
class DeleteUserCommand:
    """Command to delete user"""
    user_id: UUID
    admin_user_id: UUID


@dataclass(frozen=True)
class UpdateUserCommand:
    """Command to update user information"""
    user_id: UUID
    updates: Dict[str, Any]
    admin_user_id: Optional[UUID] = None