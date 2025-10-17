# src/summarization/application/services/summarization_metrics_service.py
from uuid import UUID
from src.metrics.domain.metrics import MetricsProvider


class SummarizationMetricsService:
    def __init__(self, metrics_provider: MetricsProvider):
        self.metrics_provider = metrics_provider

    def record_summarization_success(self, media_id: UUID, duration: float, provider: str) -> None:
        self.metrics_provider.increment_counter("SUMMARIZATIONS_TOTAL", {"status": "success"})
        self.metrics_provider.observe_histogram(
            "SUMMARIZATION_DURATION", duration, {"media_id": str(media_id), "provider": provider}
        )

    def record_summarization_failure(self) -> None:
        self.metrics_provider.increment_counter("SUMMARIZATIONS_TOTAL", {"status": "failure"})
