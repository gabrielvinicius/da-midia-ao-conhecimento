from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(slots=True)
class CreateUserCommand:
    """DTO representing a user creation request."""

    email: str
    password: str
    role: str = field(default="USER")

    def normalized_email(self) -> str:
        return self.email.strip().lower()

    def normalized_role(self) -> str:
        return (self.role or "USER").strip().lower()


__all__ = ["CreateUserCommand"]
