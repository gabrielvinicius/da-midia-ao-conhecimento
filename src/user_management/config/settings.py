"""Configuration object for authentication module."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional, Tuple


@dataclass(frozen=True)
class AuthSettings:
    """Default authentication settings with environment overrides."""

    secret_key: str = field(default_factory=lambda: os.getenv("AUTH_SECRET_KEY", "change-me"))
    algorithm: str = field(default_factory=lambda: os.getenv("AUTH_JWT_ALGORITHM", "HS256"))
    access_token_expire_minutes: int = field(
        default_factory=lambda: int(os.getenv("AUTH_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    )
    password_min_length: int = field(
        default_factory=lambda: int(os.getenv("AUTH_PASSWORD_MIN_LENGTH", "8"))
    )
    allowed_cors_origins: Tuple[str, ...] = field(
        default_factory=lambda: tuple(
            origin.strip()
            for origin in os.getenv("AUTH_ALLOWED_ORIGINS", "").split(",")
            if origin.strip()
        )
    )
    cookie_secure: bool = field(
        default_factory=lambda: os.getenv("AUTH_COOKIE_SECURE", "0").lower() in {"1", "true", "yes"}
    )
    cookie_samesite: str = field(
        default_factory=lambda: os.getenv("AUTH_COOKIE_SAMESITE", "lax").lower()
    )


@lru_cache(maxsize=1)
def get_auth_settings() -> AuthSettings:
    """Cached accessor for AuthSettings."""
    return AuthSettings()


__all__ = ["AuthSettings", "get_auth_settings"]
