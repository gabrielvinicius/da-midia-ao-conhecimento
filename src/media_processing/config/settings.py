
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
    # Arquivos abaixo deste tamanho vão para a fila rápida de transcrição,
    # para uma gravação curta não esperar atrás de uma aula de duas horas.
    fast_lane_max_mb: float = 50
    # Quadros de vídeo descritos: um a cada PROCESSING_FRAME_EVERY_SECONDS,
    # entre PROCESSING_FRAMES_MIN e PROCESSING_FRAMES_MAX (cada um custa ~4 s
    # de GPU), e a semelhança de palavras a partir da qual duas descrições
    # seguidas contam como a mesma cena e a segunda é descartada.
    frame_every_seconds: float = 180
    frames_min: int = 3
    frames_max: int = 8
    same_scene_similarity: float = 0.55

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

    def frame_sampling(self):
        from src.media_processing.domain.visual_sampling import FrameSampling

        return FrameSampling(
            seconds_per_frame=self.frame_every_seconds,
            min_frames=self.frames_min,
            max_frames=self.frames_max,
            same_scene_similarity=self.same_scene_similarity,
        )

    model_config = SettingsConfigDict(
        env_prefix="PROCESSING_",
        case_sensitive=False,
        extra="ignore",
    )


processing_settings = MediaProcessingSettings()


__all__ = ["MediaProcessingSettings", "processing_settings"]
