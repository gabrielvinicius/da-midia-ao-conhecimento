"""Shared broker/cache configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache


@dataclass(frozen=True)
class BrokerSettings:
    """Configuration for Redis broker/cache."""

    redis_host: str = field(default_factory=lambda: os.getenv("REDIS_HOST", "localhost"))
    redis_port: int = field(default_factory=lambda: int(os.getenv("REDIS_PORT", "6379")))
    redis_db: int = field(default_factory=lambda: int(os.getenv("REDIS_DB", "0")))
    redis_username: str | None = field(default_factory=lambda: os.getenv("REDIS_USERNAME"))
    redis_password: str | None = field(default_factory=lambda: os.getenv("REDIS_PASSWORD"))


@lru_cache(maxsize=1)
def get_broker_settings() -> BrokerSettings:
    """Cached accessor for BrokerSettings."""

    return BrokerSettings()


__all__ = ["BrokerSettings", "get_broker_settings"]
