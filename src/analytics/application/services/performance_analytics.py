"""
Performance Analytics Service - Single Responsibility: Performance analysis
Follows SRP by handling only performance-related analytics.
"""
from typing import Dict, List, Any
from datetime import datetime, timedelta
import structlog

from src.analytics.domain.interfaces import IPerformanceAnalytics, IAnalyticsRepository, TimeRange

logger = structlog.get_logger(__name__)


class PerformanceAnalytics(IPerformanceAnalytics):
    """
    Service responsible ONLY for performance analytics operations.
    
    Single Responsibility: Handle performance analysis and optimization insights.
    Open/Closed: Extensible for new performance metrics.
    Dependency Inversion: Depends on repository abstraction.
    """
    
    def __init__(self, analytics_repo: IAnalyticsRepository):
        self.analytics_repo = analytics_repo
    
    async def calculate_throughput_metrics(self, time_range: TimeRange) -> Dict[str, Any]:
        """
        Calculate system throughput metrics.
        
        Args:
            time_range: Time range for analysis
            
        Returns:
            Dictionary with throughput metrics
        """
        success_rates = await self.analytics_repo.get_success_failure_rates(time_range)
        
        # Calculate throughput based on time range
        hours_in_range = self._get_hours_in_range(time_range)
        
        media_throughput = success_rates["media"]["total"] / hours_in_range if hours_in_range > 0 else 0
        transcription_throughput = success_rates["transcription"]["total"] / hours_in_range if hours_in_range > 0 else 0
        summarization_throughput = success_rates["summarization"]["total"] / hours_in_range if hours_in_range > 0 else 0
        
        return {
            "time_range": time_range.value,
            "analysis_period_hours": hours_in_range,
            "throughput_metrics": {
                "media_per_hour": round(media_throughput, 2),
                "transcriptions_per_hour": round(transcription_throughput, 2),
                "summaries_per_hour": round(summarization_throughput, 2),
                "total_operations_per_hour": round(media_throughput + transcription_throughput + summarization_throughput, 2)
            },
            "efficiency_metrics": {
                "media_success_rate": success_rates["media"]["success_rate"],
                "transcription_success_rate": success_rates["transcription"]["success_rate"],
                "summarization_success_rate": success_rates["summarization"]["success_rate"]
            },
            "capacity_utilization": self._calculate_capacity_utilization(success_rates)
        }
    
    async def analyze_bottlenecks(self) -> Dict[str, Any]:
        """
        Identify system bottlenecks.
        
        Returns:
            Dictionary with bottleneck analysis
        """
        # Get processing times for different operations
        from src.analytics.domain.interfaces import ProcessingType
        
        transcription_times = await self.analytics_repo.get_processing_times_by_type(ProcessingType.TRANSCRIPTION)
        summarization_times = await self.analytics_repo.get_processing_times_by_type(ProcessingType.SUMMARIZATION)
        
        # Get success rates
        week_rates = await self.analytics_repo.get_success_failure_rates(TimeRange.LAST_WEEK)
        
        bottlenecks = []
        recommendations = []
        
        # Identify bottlenecks based on processing times
        if transcription_times["avg_seconds"] > 300:  # 5 minutes
            bottlenecks.append({
                "type": "transcription_slow",
                "severity": "high" if transcription_times["avg_seconds"] > 600 else "medium",
                "metric": f"Average transcription time: {transcription_times['avg_seconds']:.1f}s"
            })
            recommendations.append("Consider optimizing transcription service or scaling resources")
        
        if summarization_times["avg_seconds"] > 120:  # 2 minutes
            bottlenecks.append({
                "type": "summarization_slow", 
                "severity": "high" if summarization_times["avg_seconds"] > 300 else "medium",
                "metric": f"Average summarization time: {summarization_times['avg_seconds']:.1f}s"
            })
            recommendations.append("Consider optimizing summarization service")
        
        # Identify bottlenecks based on failure rates
        if week_rates["transcription"]["success_rate"] < 85:
            bottlenecks.append({
                "type": "transcription_failures",
                "severity": "high",
                "metric": f"Transcription success rate: {week_rates['transcription']['success_rate']:.1f}%"
            })
            recommendations.append("Investigate transcription failures")
        
        if week_rates["summarization"]["success_rate"] < 85:
            bottlenecks.append({
                "type": "summarization_failures",
                "severity": "high", 
                "metric": f"Summarization success rate: {week_rates['summarization']['success_rate']:.1f}%"
            })
            recommendations.append("Investigate summarization failures")
        
        # Calculate overall bottleneck score
        severity_scores = {"high": 3, "medium": 2, "low": 1}
        bottleneck_score = sum(severity_scores.get(b["severity"], 0) for b in bottlenecks)
        
        return {
            "bottleneck_score": bottleneck_score,
            "severity_level": self._get_severity_level(bottleneck_score),
            "identified_bottlenecks": bottlenecks,
            "recommendations": recommendations,
            "performance_summary": {
                "transcription_avg_time": transcription_times["avg_seconds"],
                "summarization_avg_time": summarization_times["avg_seconds"],
                "overall_success_rate": (
                    week_rates["transcription"]["success_rate"] + 
                    week_rates["summarization"]["success_rate"]
                ) / 2
            }
        }
    
    async def get_resource_utilization(self) -> Dict[str, Any]:
        """
        Get resource utilization metrics.
        
        Returns:
            Dictionary with resource utilization data
        """
        # Get current processing status
        week_metrics = await self.analytics_repo.get_success_failure_rates(TimeRange.LAST_WEEK)
        user_metrics = await self.analytics_repo.get_user_activity_metrics()
        
        # Calculate utilization metrics
        total_operations = (
            week_metrics["media"]["total"] +
            week_metrics["transcription"]["total"] + 
            week_metrics["summarization"]["total"]
        )
        
        # Estimate resource usage (placeholder calculations)
        estimated_cpu_usage = min(100, (total_operations / 100) * 10)  # Rough estimate
        estimated_memory_usage = min(100, (total_operations / 50) * 15)  # Rough estimate
        estimated_storage_growth = user_metrics["total_media"] * 0.1  # GB estimate
        
        return {
            "analysis_period": "last_week",
            "operational_metrics": {
                "total_operations": total_operations,
                "operations_per_day": total_operations / 7,
                "active_users": user_metrics["total_users"]
            },
            "estimated_resource_usage": {
                "cpu_utilization_percent": round(estimated_cpu_usage, 1),
                "memory_utilization_percent": round(estimated_memory_usage, 1),
                "storage_growth_gb": round(estimated_storage_growth, 2)
            },
            "efficiency_indicators": {
                "operations_per_user": round(total_operations / user_metrics["total_users"], 1) if user_metrics["total_users"] > 0 else 0,
                "success_ratio": week_metrics["media"]["success_rate"] / 100,
                "resource_efficiency_score": self._calculate_efficiency_score(total_operations, estimated_cpu_usage)
            }
        }
    
    async def predict_processing_load(self, hours_ahead: int = 24) -> Dict[str, Any]:
        """
        Predict processing load for the next N hours.
        
        Args:
            hours_ahead: Number of hours to predict
            
        Returns:
            Dictionary with load predictions
        """
        # Get historical data for prediction baseline
        week_metrics = await self.analytics_repo.get_success_failure_rates(TimeRange.LAST_WEEK)
        day_metrics = await self.analytics_repo.get_success_failure_rates(TimeRange.LAST_DAY)
        
        # Simple prediction based on recent trends
        weekly_avg_per_hour = week_metrics["media"]["total"] / (7 * 24)
        daily_avg_per_hour = day_metrics["media"]["total"] / 24
        
        # Weight recent data more heavily
        predicted_hourly_load = (daily_avg_per_hour * 0.7) + (weekly_avg_per_hour * 0.3)
        
        # Generate hourly predictions with some variation
        predictions = []
        for hour in range(hours_ahead):
            # Add some realistic variation (business hours vs off-hours)
            hour_of_day = (datetime.utcnow().hour + hour) % 24
            business_hour_multiplier = 1.5 if 9 <= hour_of_day <= 17 else 0.7
            
            predicted_load = predicted_hourly_load * business_hour_multiplier
            predictions.append({
                "hour": hour + 1,
                "timestamp": (datetime.utcnow() + timedelta(hours=hour + 1)).isoformat(),
                "predicted_media_uploads": round(predicted_load, 1),
                "predicted_processing_load": round(predicted_load * 2, 1),  # Processing takes ~2x resources
                "confidence": "medium"
            })
        
        # Calculate peak and low periods
        loads = [p["predicted_processing_load"] for p in predictions]
        peak_load = max(loads)
        low_load = min(loads)
        
        return {
            "prediction_horizon_hours": hours_ahead,
            "baseline_metrics": {
                "weekly_avg_per_hour": round(weekly_avg_per_hour, 1),
                "daily_avg_per_hour": round(daily_avg_per_hour, 1)
            },
            "predictions": predictions,
            "summary": {
                "peak_load": peak_load,
                "low_load": low_load,
                "average_load": round(sum(loads) / len(loads), 1),
                "load_variance": round(peak_load - low_load, 1)
            },
            "recommendations": self._generate_load_recommendations(peak_load, low_load)
        }
    
    def _get_hours_in_range(self, time_range: TimeRange) -> int:
        """Get number of hours in time range."""
        if time_range == TimeRange.LAST_HOUR:
            return 1
        elif time_range == TimeRange.LAST_DAY:
            return 24
        elif time_range == TimeRange.LAST_WEEK:
            return 24 * 7
        elif time_range == TimeRange.LAST_MONTH:
            return 24 * 30
        elif time_range == TimeRange.LAST_YEAR:
            return 24 * 365
        else:
            return 24  # Default to day
    
    def _calculate_capacity_utilization(self, success_rates: Dict) -> Dict[str, float]:
        """Calculate capacity utilization metrics."""
        total_operations = (
            success_rates["media"]["total"] +
            success_rates["transcription"]["total"] +
            success_rates["summarization"]["total"]
        )
        
        # Rough capacity estimates (would be configured based on actual system)
        estimated_max_capacity = 1000  # operations per time period
        
        return {
            "current_utilization_percent": min(100, (total_operations / estimated_max_capacity) * 100),
            "remaining_capacity_percent": max(0, 100 - ((total_operations / estimated_max_capacity) * 100)),
            "operations_to_capacity": max(0, estimated_max_capacity - total_operations)
        }
    
    def _get_severity_level(self, bottleneck_score: int) -> str:
        """Get severity level based on bottleneck score."""
        if bottleneck_score >= 6:
            return "critical"
        elif bottleneck_score >= 3:
            return "high"
        elif bottleneck_score >= 1:
            return "medium"
        else:
            return "low"
    
    def _calculate_efficiency_score(self, total_operations: int, cpu_usage: float) -> float:
        """Calculate resource efficiency score."""
        if cpu_usage == 0:
            return 100.0
        
        efficiency = (total_operations / cpu_usage) * 10  # Rough calculation
        return min(100.0, max(0.0, efficiency))
    
    def _generate_load_recommendations(self, peak_load: float, low_load: float) -> List[str]:
        """Generate recommendations based on predicted load."""
        recommendations = []
        
        if peak_load > 50:
            recommendations.append("Consider scaling up resources during peak hours")
        
        if low_load < 5:
            recommendations.append("Consider scaling down resources during low activity periods")
        
        if peak_load / low_load > 5:  # High variance
            recommendations.append("Implement auto-scaling to handle load variations")
        
        return recommendations