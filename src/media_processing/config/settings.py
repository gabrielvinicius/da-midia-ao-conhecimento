
from pydantic_settings import BaseSettings, SettingsConfigDict


class MediaProcessingSettings(BaseSettings):
    """Media-processing/worker specific settings."""

    # Mídia parada (ver ProcessingDeadlinePolicy). Variáveis PROCESSING_STALL_*.
    stall_check_interval_seconds: int = 300
    stall_safety_factor: float = 3.0
    stall_minimum_minutes: float = 20
    stall_maximum_hours: float = 6
    stall_unknown_duration_minutes: float = 60
    stall_queue_hours: float = 24
    stall_fallback_realtime_factor: float = 1.0

    def deadline_policy(self):
        from src.media_processing.domain.processing_deadline import (
            ProcessingDeadlinePolicy,
        )

        return ProcessingDeadlinePolicy(
            safety_factor=self.stall_safety_factor,
            minimum_seconds=self.stall_minimum_minutes * 60,
            maximum_seconds=self.stall_maximum_hours * 3600,
            fallback_realtime_factor=self.stall_fallback_realtime_factor,
            unknown_duration_seconds=self.stall_unknown_duration_minutes * 60,
            queue_seconds=self.stall_queue_hours * 3600,
        )

    model_config = SettingsConfigDict(
        env_prefix="PROCESSING_",
        case_sensitive=False,
        extra="ignore",
    )


processing_settings = MediaProcessingSettings()


__all__ = ["MediaProcessingSettings", "processing_settings"]
