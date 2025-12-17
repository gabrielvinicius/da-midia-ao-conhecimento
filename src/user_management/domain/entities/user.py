from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID, uuid4


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    USER = "USER"

    @classmethod
    def normalize(cls, value: str) -> "UserRole":
        try:
            return cls(value.upper())
        except Exception:
            return cls.USER


@dataclass
class User:
    id: UUID
    email: str
    password_hash: str
    role: UserRole
    is_active: bool = True

    @classmethod
    def create(
        cls,
        email: str,
        password_hash: str,
        role: UserRole | str = UserRole.USER,
    ) -> "User":
        role_enum = role if isinstance(role, UserRole) else UserRole.normalize(str(role))
        return cls(id=uuid4(), email=email, password_hash=password_hash, role=role_enum)

    def activate(self) -> None:
        self.is_active = True

    def deactivate(self) -> None:
        self.is_active = False


__all__ = ["User", "UserRole"]
