"""Domain entities for user management."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import uuid4

from src.shared.domain.base_entity import AggregateRoot


class UserRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"


@dataclass(kw_only=True, slots=True)
class User(AggregateRoot):
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