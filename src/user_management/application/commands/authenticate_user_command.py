from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthenticateUserCommand:
    """DTO representing a user authentication request."""

    email: str
    password: str


__all__ = ["AuthenticateUserCommand"]
