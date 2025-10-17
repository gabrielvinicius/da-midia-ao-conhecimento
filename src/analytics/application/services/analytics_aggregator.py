"""
Analytics Aggregator Service - Single Responsibility: Data aggregation operations.
Follows SRP by handling only data aggregation and preprocessing concerns.
"""
from typing import Dict, Any
from datetime import datetime, timedelta
import structlog

from src.analytics.domain.interfaces import IAnalyticsAggregator, IAnalyticsRepository, TimeRange
from src.analytics.application.services.analytics_validator import AnalyticsValidator

logger = structlog.get_logger(__name__)


class AnalyticsAggregator(IAnalyticsAggregator):
    """
    Aggregates analytics data following SRP.
    Single responsibility: Aggregate and preprocess analytics data.
    """
    
    def __init__(self, analytics_repo: IAnalyticsRepository, validator: AnalyticsValidator):
        self._analytics_repo = analytics_repo
        self._validator = validator
    
    async def aggregate_performance_data(self, time_range: TimeRange) -> Dict[str, Any]:
        """
        Aggregate performance data for time range.
        
        Args:
            time_range: Time range for aggregation
            
        Returns:
            Dict with aggregated performance data
        """
        self._validator.validate_time_range(time_range)
        
        # Get raw data
        success_rates = await self._analytics_repo.get_success_failure_rates(time_range)
        user_metrics = await self._analytics_repo.get_user_activity_metrics()
        
        # Aggregate performance metrics
        aggregated_data = {
            "time_range": time_range.value,
            "aggregation_timestamp": datetime.utcnow().isoformat(),
            "service_performance": self._aggregate_service_performance(success_rates),
            "throughput_metrics": self._calculate_throughput_metrics(success_rates, time_range),
            "user_engagement": self._aggregate_user_engagement(user_metrics),
            "system_health": self._calculate_system_health(success_rates)
        }
        
        logger.info(
            "analytics.aggregation.performance_completed",
            time_range=time_range.value,
            services_analyzed=len(success_rates)
        )
        
        return aggregated_data
    
    async def aggregate_quality_data(self, time_range: TimeRange) -> Dict[str, Any]:
        """
        Aggregate quality data for time range.
        
        Args:
            time_range: Time range for aggregation
            
        Returns:
            Dict with aggregated quality data
        """
        self._validator.validate_time_range(time_range)
        
        # Get raw quality data
        success_rates = await self._analytics_repo.get_success_failure_rates(time_range)
        
        # Import processing types dynamically to avoid circular imports
        from src.analytics.domain.interfaces import ProcessingType
        
        transcription_times = await self._analytics_repo.get_processing_times_by_type(ProcessingType.TRANSCRIPTION)
        summarization_times = await self._analytics_repo.get_processing_times_by_type(ProcessingType.SUMMARIZATION)
        
        # Aggregate quality metrics
        aggregated_data = {
            "time_range": time_range.value,
            "aggregation_timestamp": datetime.utcnow().isoformat(),
            "quality_scores": self._aggregate_quality_scores(success_rates, transcription_times, summarization_times),
            "reliability_metrics": self._aggregate_reliability_metrics(success_rates),
            "performance_consistency": self._aggregate_performance_consistency(transcription_times, summarization_times),
            "error_analysis": self._aggregate_error_patterns(success_rates)
        }
        
        logger.info(
            "analytics.aggregation.quality_completed",
            time_range=time_range.value,
            quality_metrics_calculated=len(aggregated_data["quality_scores"])
        )
        
        return aggregated_data
    
    async def aggregate_user_metrics(self, time_range: TimeRange) -> Dict[str, Any]:
        """
        Aggregate user activity metrics.
        
        Args:
            time_range: Time range for aggregation
            
        Returns:
            Dict with aggregated user metrics
        """
        self._validator.validate_time_range(time_range)
        
        # Get user activity data
        user_metrics = await self._analytics_repo.get_user_activity_metrics()
        success_rates = await self._analytics_repo.get_success_failure_rates(time_range)
        
        # Aggregate user-focused metrics
        aggregated_data = {
            "time_range": time_range.value,
            "aggregation_timestamp": datetime.utcnow().isoformat(),
            "user_activity": self._aggregate_user_activity(user_metrics),
            "usage_patterns": self._aggregate_usage_patterns(success_rates, user_metrics),
            "user_satisfaction": self._estimate_user_satisfaction(success_rates),
            "adoption_metrics": self._calculate_adoption_metrics(user_metrics)
        }
        
        logger.info(
            "analytics.aggregation.user_metrics_completed",
            time_range=time_range.value,
            total_users=user_metrics.get("total_users", 0)
        )
        
        return aggregated_data
    
    def _aggregate_service_performance(self, success_rates: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate service performance metrics."""
        services = ["media", "transcription", "summarization"]
        
        aggregated = {}
        for service in services:
            if service in success_rates:
                service_data = success_rates[service]
                aggregated[service] = {
                    "success_rate": service_data.get("success_rate", 0),
                    "total_operations": service_data.get("total", 0),
                    "successful_operations": service_data.get("successful", 0),
                    "failed_operations": service_data.get("failed", 0),
                    "performance_grade": self._calculate_performance_grade(service_data.get("success_rate", 0))
                }
        
        return aggregated
    
    def _calculate_throughput_metrics(self, success_rates: Dict[str, Any], time_range: TimeRange) -> Dict[str, Any]:
        """Calculate aggregated throughput metrics."""
        hours_in_range = self._get_hours_in_range(time_range)
        
        total_operations = sum(
            success_rates.get(service, {}).get("total", 0)
            for service in ["media", "transcription", "summarization"]
        )
        
        return {
            "total_operations": total_operations,
            "operations_per_hour": total_operations / hours_in_range if hours_in_range > 0 else 0,
            "operations_per_day": total_operations / (hours_in_range / 24) if hours_in_range > 0 else 0,
            "peak_capacity_utilization": min(100, (total_operations / (hours_in_range * 10)) * 100) if hours_in_range > 0 else 0
        }
    
    def _aggregate_user_engagement(self, user_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate user engagement metrics."""
        total_users = user_metrics.get("total_users", 0)
        total_media = user_metrics.get("total_media", 0)
        
        return {
            "total_active_users": total_users,
            "total_media_processed": total_media,
            "average_media_per_user": total_media / total_users if total_users > 0 else 0,
            "engagement_level": self._calculate_engagement_level(total_media, total_users)
        }
    
    def _calculate_system_health(self, success_rates: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall system health metrics."""
        service_success_rates = [
            success_rates.get(service, {}).get("success_rate", 0)
            for service in ["media", "transcription", "summarization"]
        ]
        
        avg_success_rate = sum(service_success_rates) / len(service_success_rates) if service_success_rates else 0
        
        health_status = "excellent" if avg_success_rate >= 95 else \
                       "good" if avg_success_rate >= 85 else \
                       "fair" if avg_success_rate >= 70 else "poor"
        
        return {
            "overall_success_rate": avg_success_rate,
            "health_status": health_status,
            "healthy_services": sum(1 for rate in service_success_rates if rate >= 90),
            "total_services": len(service_success_rates)
        }
    
    def _aggregate_quality_scores(self, success_rates: Dict, transcription_times: Dict, summarization_times: Dict) -> Dict[str, float]:
        """Aggregate quality scores."""
        return {
            "transcription_quality": self._calculate_service_quality_score(
                success_rates.get("transcription", {}), transcription_times
            ),
            "summarization_quality": self._calculate_service_quality_score(
                success_rates.get("summarization", {}), summarization_times
            ),
            "overall_quality": self._calculate_overall_quality_score(success_rates)
        }
    
    def _calculate_service_quality_score(self, service_rates: Dict, timing_data: Dict) -> float:
        """Calculate quality score for a specific service."""
        success_rate = service_rates.get("success_rate", 0)
        
        # Calculate consistency score based on timing variation
        avg_time = timing_data.get("avg_seconds", 0)
        min_time = timing_data.get("min_seconds", 0) 
        max_time = timing_data.get("max_seconds", 0)
        
        if avg_time > 0:
            consistency = max(0, 100 - ((max_time - min_time) / avg_time * 100))
        else:
            consistency = 100
        
        # Weighted quality score
        quality_score = (success_rate * 0.7) + (consistency * 0.3)
        return round(quality_score, 2)
    
    def _calculate_overall_quality_score(self, success_rates: Dict) -> float:
        """Calculate overall system quality score."""
        service_rates = [
            success_rates.get(service, {}).get("success_rate", 0)
            for service in ["transcription", "summarization"]
        ]
        
        return round(sum(service_rates) / len(service_rates) if service_rates else 0, 2)
    
    def _get_hours_in_range(self, time_range: TimeRange) -> int:
        """Get number of hours in time range."""
        range_hours = {
            TimeRange.LAST_HOUR: 1,
            TimeRange.LAST_DAY: 24,
            TimeRange.LAST_WEEK: 168,
            TimeRange.LAST_MONTH: 720,
            TimeRange.LAST_YEAR: 8760
        }
        return range_hours.get(time_range, 24)
    
    def _calculate_performance_grade(self, success_rate: float) -> str:
        """Calculate performance grade based on success rate."""
        if success_rate >= 95:
            return "A"
        elif success_rate >= 85:
            return "B"
        elif success_rate >= 70:
            return "C"
        elif success_rate >= 50:
            return "D"
        else:
            return "F"
    
    def _calculate_engagement_level(self, total_media: int, total_users: int) -> str:
        """Calculate user engagement level."""
        if total_users == 0:
            return "none"
        
        media_per_user = total_media / total_users
        
        if media_per_user >= 10:
            return "high"
        elif media_per_user >= 5:
            return "medium"
        elif media_per_user >= 1:
            return "low"
        else:
            return "minimal"