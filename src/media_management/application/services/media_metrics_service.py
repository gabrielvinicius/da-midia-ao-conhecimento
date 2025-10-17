# src/media_management/application/services/media_metrics_service.py
from uuid import UUID
from src.metrics.application.metrics_service import MetricsService


class MediaMetricsService:
    def __init__(self, metrics_service: MetricsService):
        self.metrics_service = metrics_service

    def record_upload_success(self, media_id: UUID, duration: float, provider: str) -> None:
        self.metrics_service.increment_media_upload("success")
        self.metrics_service.observe_upload_duration(
            media_id=str(media_id), duration=duration, provider=provider
        )

    def record_upload_failure(self) -> None:
        self.metrics_service.increment_media_upload("failure")
