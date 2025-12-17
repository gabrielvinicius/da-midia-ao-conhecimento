from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class StorageSettings(BaseSettings):
    """Storage bounded-context settings."""

    providers_allowed: List[str] = ["local", "s3"]

    model_config = SettingsConfigDict(
        env_prefix="STORAGE_",
        case_sensitive=False,
        extra="ignore",
    )


storage_settings = StorageSettings()


__all__ = ["StorageSettings", "storage_settings"]
