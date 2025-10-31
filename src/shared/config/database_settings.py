"""Database configuration helpers used during testing."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class DatabaseSettings:
    """Simple settings object with sane defaults for the test suite."""

    database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./app.db")

    @property
    def sync_database_url(self) -> str:
        """Return a synchronous database URL for SQLAlchemy's sync engine."""
        if self.database_url.startswith("sqlite+aiosqlite"):
            return self.database_url.replace("+aiosqlite", "")
        return os.getenv("SYNC_DATABASE_URL", self.database_url)


__all__ = ["DatabaseSettings"]
