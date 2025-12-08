from dataclasses import dataclass
from uuid import UUID

from src.user_management.domain.user import UserRole


@dataclass(frozen=True)
class CreateUserCommand:
    email: str
    password: str
    role: UserRole = UserRole.USER


@dataclass(frozen=True)
class UpdateUserCommand:
    user_id: UUID
    email: str | None = None
    password: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None


@dataclass(frozen=True)
class DeleteUserCommand:
    user_id: UUID
