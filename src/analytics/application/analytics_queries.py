# src/analytics/application/analytics_queries.py
from src.analytics.infrastructure.analytics_repository import AnalyticsRepository
from src.analytics.config.settings import AnalyticsSettings


class AnalyticsQueries:
    """Handles read-only operations for analytics."""
    def __init__(self, analytics_repo: AnalyticsRepository, settings: AnalyticsSettings):
        self.analytics_repo = analytics_repo
        self.settings = settings

    async def estimate_processing_time(self, content_metric: float) -> dict:
        """Estimates the total processing time based on a content metric (e.g., duration, length) and historical data."""
        historical_data = await self.analytics_repo.get_average_processing_times()

        # Use the correct key from the refactored repository
        if historical_data["total_media_analyzed"] == 0:
            # Use default estimates from settings
            transcription_est = content_metric * self.settings.default_transcription_factor
            summarization_est = self.settings.default_summarization_seconds
            confidence = "low"
        else:
            # Use historical average times
            transcription_est = historical_data["transcription_avg_seconds"]
            summarization_est = historical_data["summarization_avg_seconds"]
            confidence = "high" if historical_data["total_media_analyzed"] > self.settings.high_confidence_threshold else "medium"

        total_est = transcription_est + summarization_est

        return {
            "estimated_total_seconds": total_est,
            "transcription_estimated_seconds": transcription_est,
            "summarization_estimated_seconds": summarization_est,
            "confidence_level": confidence
        }
