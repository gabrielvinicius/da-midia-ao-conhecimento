# src/transcription/application/services/transcription_metrics_service.py
from uuid import UUID
from src.metrics.domain.metrics import MetricsProvider


class TranscriptionMetricsService:
    def __init__(self, metrics_provider: MetricsProvider):
        self.metrics_provider = metrics_provider

    def record_transcription_success(self, media_id: UUID, duration: float, provider: str) -> None:
        self.metrics_provider.increment_counter("TRANSCRIPTIONS_TOTAL", {"status": "success"})
        self.metrics_provider.observe_histogram(
            "TRANSCRIPTION_DURATION", duration, {"media_id": str(media_id), "provider": provider}
        )

    def record_transcription_failure(self) -> None:
        self.metrics_provider.increment_counter("TRANSCRIPTIONS_TOTAL", {"status": "failure"})
