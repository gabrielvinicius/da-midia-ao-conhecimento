# src/analytics/application/analytics_queries.py
from typing import Any, Dict, List
from uuid import UUID

import structlog

from src.monitoring.config.settings import AnalyticsSettings
from src.monitoring.domain.interfaces import (
    IAnalyticsQueries,
    IAnalyticsRepository,
    TimeRange,
)

logger = structlog.get_logger(__name__)


class AnalyticsQueries(IAnalyticsQueries):
    """Analytics queries service following SOLID principles.
    
    Single Responsibility: Handle analytics query operations.
    Dependency Inversion: Depends on repository abstraction.
    """

    def __init__(self, analytics_repo: IAnalyticsRepository, settings: AnalyticsSettings):
        self.analytics_repo = analytics_repo
        self.settings = settings

    async def estimate_processing_time(self, content_metric: float) -> Dict[str, Any]:
        """Estimates the total processing time based on content metric and historical data.
        
        Args:
            content_metric: Content metric (e.g., duration, length)
            
        Returns:
            Dictionary with processing time estimates

        """
        historical_data = await self.analytics_repo.get_average_processing_times()

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

        logger.info(
            "analytics.processing_time_estimated",
            content_metric=content_metric,
            total_estimate=total_est,
            confidence=confidence
        )

        return {
            "estimated_total_seconds": total_est,
            "transcription_estimated_seconds": transcription_est,
            "summarization_estimated_seconds": summarization_est,
            "confidence_level": confidence,
            "based_on_samples": historical_data["total_media_analyzed"]
        }

    async def get_system_performance_metrics(self, time_range: TimeRange) -> Dict[str, Any]:
        """Get comprehensive system performance metrics.
        
        Args:
            time_range: Time range for analysis
            
        Returns:
            Dictionary with performance metrics

        """
        # Get success/failure rates
        success_rates = await self.analytics_repo.get_success_failure_rates(time_range)

        # Get user activity metrics
        user_metrics = await self.analytics_repo.get_user_activity_metrics()

        # Get media type distribution
        media_distribution = await self.analytics_repo.get_media_type_distribution()

        # Calculate overall system health score
        overall_success_rate = success_rates["media"]["success_rate"]
        health_score = self._calculate_health_score(success_rates, user_metrics)

        return {
            "time_range": time_range.value,
            "overall_health_score": health_score,
            "success_rates": success_rates,
            "user_metrics": user_metrics,
            "media_distribution": media_distribution,
            "recommendations": self._generate_recommendations(success_rates, user_metrics)
        }

    async def get_processing_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get processing trends over time.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with trend analysis

        """
        # For now, we'll use week-based analysis as a starting point
        # In a real implementation, this would do day-by-day analysis

        current_week = await self.analytics_repo.get_success_failure_rates(TimeRange.LAST_WEEK)
        last_month = await self.analytics_repo.get_success_failure_rates(TimeRange.LAST_MONTH)

        # Calculate trend indicators
        current_success_rate = current_week["media"]["success_rate"]
        monthly_success_rate = last_month["media"]["success_rate"]

        trend_direction = "stable"
        if current_success_rate > monthly_success_rate + 5:
            trend_direction = "improving"
        elif current_success_rate < monthly_success_rate - 5:
            trend_direction = "declining"

        return {
            "analysis_period_days": days,
            "current_week": current_week,
            "monthly_average": last_month,
            "trend_direction": trend_direction,
            "trend_percentage": current_success_rate - monthly_success_rate,
            "insights": self._generate_trend_insights(current_week, last_month)
        }

    async def get_user_analytics(self, user_id: UUID) -> Dict[str, Any]:
        """Get analytics for specific user.
        
        Args:
            user_id: User ID to analyze
            
        Returns:
            Dictionary with user-specific analytics

        """
        user_metrics = await self.analytics_repo.get_user_activity_metrics(user_id)
        overall_metrics = await self.analytics_repo.get_user_activity_metrics()

        # Calculate user ranking and percentiles
        user_rank = self._calculate_user_rank(user_metrics, overall_metrics)

        return {
            "user_id": str(user_id),
            "metrics": user_metrics,
            "ranking": user_rank,
            "comparison_to_average": {
                "media_count_vs_avg": user_metrics["total_media"] - overall_metrics["avg_media_per_user"],
                "success_rate_vs_avg": user_metrics["success_rate"] - overall_metrics["overall_success_rate"]
            },
            "recommendations": self._generate_user_recommendations(user_metrics, overall_metrics)
        }

    async def get_media_analytics(self, media_id: UUID) -> Dict[str, Any]:
        """Get analytics for specific media item.
        
        Args:
            media_id: Media ID to analyze
            
        Returns:
            Dictionary with media-specific analytics

        """
        # This would require additional repository methods to get media-specific data
        # For now, return a placeholder structure

        return {
            "media_id": str(media_id),
            "processing_timeline": [],  # Would contain processing events
            "performance_metrics": {},  # Would contain processing times
            "quality_metrics": {},      # Would contain quality assessments
            "comparison_metrics": {}    # Would compare to similar media
        }

    def _calculate_health_score(self, success_rates: Dict, user_metrics: Dict) -> float:
        """Calculate overall system health score (0-100)."""
        media_success = success_rates["media"]["success_rate"]
        transcription_success = success_rates["transcription"]["success_rate"]
        summarization_success = success_rates["summarization"]["success_rate"]

        # Weighted average with media being most important
        health_score = (
            media_success * 0.5 +
            transcription_success * 0.3 +
            summarization_success * 0.2
        )

        return round(health_score, 2)

    def _generate_recommendations(self, success_rates: Dict, user_metrics: Dict) -> List[str]:
        """Generate system recommendations based on metrics."""
        recommendations = []

        if success_rates["media"]["success_rate"] < 90:
            recommendations.append("Consider investigating media processing failures")

        if success_rates["transcription"]["success_rate"] < 85:
            recommendations.append("Transcription service may need optimization")

        if success_rates["summarization"]["success_rate"] < 85:
            recommendations.append("Summarization service may need attention")

        if user_metrics["avg_media_per_user"] < 1:
            recommendations.append("Consider user engagement initiatives")

        return recommendations

    def _generate_trend_insights(self, current: Dict, historical: Dict) -> List[str]:
        """Generate insights based on trend analysis."""
        insights = []

        current_rate = current["media"]["success_rate"]
        historical_rate = historical["media"]["success_rate"]

        if current_rate > historical_rate:
            insights.append("System performance is improving")
        elif current_rate < historical_rate:
            insights.append("System performance shows decline")
        else:
            insights.append("System performance is stable")

        # Add volume insights
        if current["media"]["total"] > historical["media"]["total"] * 0.25:  # 25% of monthly in a week
            insights.append("Processing volume is high")

        return insights

    def _calculate_user_rank(self, user_metrics: Dict, overall_metrics: Dict) -> Dict[str, Any]:
        """Calculate user ranking and performance tier."""
        total_media = user_metrics["total_media"]
        avg_media = overall_metrics["avg_media_per_user"]

        if total_media >= avg_media * 2:
            tier = "power_user"
        elif total_media >= avg_media:
            tier = "active_user"
        elif total_media > 0:
            tier = "casual_user"
        else:
            tier = "inactive_user"

        return {
            "tier": tier,
            "percentile": min(95, max(5, (total_media / avg_media) * 50))  # Rough percentile
        }

    def _generate_user_recommendations(self, user_metrics: Dict, overall_metrics: Dict) -> List[str]:
        """Generate user-specific recommendations."""
        recommendations = []

        if user_metrics["success_rate"] < overall_metrics["overall_success_rate"]:
            recommendations.append("Consider reviewing media quality guidelines")

        if user_metrics["total_media"] == 0:
            recommendations.append("Try uploading your first media file")
        elif user_metrics["total_media"] < 5:
            recommendations.append("Explore more features by uploading additional content")

        return recommendations
