from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class MediaProcessingSettings(BaseSettings):
    """Media-processing/worker specific settings."""

    transcription_providers_allowed: List[str] = [
        "whisper",
        "fastwhisper",
        "mock",
        "mock_whisper",
    ]

    model_config = SettingsConfigDict(
        env_prefix="PROCESSING_",
        case_sensitive=False,
        extra="ignore",
    )


processing_settings = MediaProcessingSettings()


__all__ = ["MediaProcessingSettings", "processing_settings"]
