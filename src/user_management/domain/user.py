"""Domain entities for user management."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4


class UserRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"


@dataclass(slots=True)
class User:
    id: UUID
    email: str
    password_hash: str
    is_active: bool = True
    role: UserRole = UserRole.USER

    @classmethod
    def create(
        cls, 
        email: str, 
        password_hash: str, 
        role: UserRole = UserRole.USER,
        is_active: bool = True
    ) -> "User":
        """Factory method to create a new user with a fresh ID."""
        return cls(
            id=uuid4(),
            email=email,
            password_hash=password_hash,
            role=role,
            is_active=is_active
        )