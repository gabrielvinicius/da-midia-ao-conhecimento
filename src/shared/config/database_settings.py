"""Database configuration helpers used during testing."""
from __future__ import annotations

from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Simple settings object with sane defaults for the test suite."""

    DB_SCHEME: str = "postgresql+asyncpg"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "video_summarizer"

    @property
    def database_url(self) -> str:
        """Construct the full asynchronous database connection string."""
        return f"{self.DB_SCHEME}://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def sync_database_url(self) -> str:
        """Return a synchronous database URL for SQLAlchemy's sync engine."""
        return self.database_url.replace("+asyncpg", "")

    class Config:
        """Pydantic-settings configuration."""

        env_file = ".env.test"
        env_file_encoding = "utf-8"
        extra = "ignore"


__all__ = ["DatabaseSettings"]
