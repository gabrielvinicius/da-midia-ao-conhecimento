"""
Quality Analytics Service - Single Responsibility: Quality analysis
Follows SRP by handling only quality-related analytics.
"""
from typing import Dict, List, Any
from datetime import datetime, timedelta
import structlog

from src.analytics.domain.interfaces import IQualityAnalytics, IAnalyticsRepository, ProcessingType, TimeRange

logger = structlog.get_logger(__name__)


class QualityAnalytics(IQualityAnalytics):
    """
    Service responsible ONLY for quality analytics operations.
    
    Single Responsibility: Handle quality analysis and accuracy metrics.
    Open/Closed: Extensible for new quality metrics.
    Dependency Inversion: Depends on repository abstraction.
    """
    
    def __init__(self, analytics_repo: IAnalyticsRepository):
        self.analytics_repo = analytics_repo
    
    async def get_processing_quality_metrics(self) -> Dict[str, Any]:
        """
        Get processing quality metrics.
        
        Returns:
            Dictionary with quality metrics
        """
        # Get success rates for quality assessment
        week_rates = await self.analytics_repo.get_success_failure_rates(TimeRange.LAST_WEEK)
        month_rates = await self.analytics_repo.get_success_failure_rates(TimeRange.LAST_MONTH)
        
        # Get processing times for quality assessment
        transcription_times = await self.analytics_repo.get_processing_times_by_type(ProcessingType.TRANSCRIPTION)
        summarization_times = await self.analytics_repo.get_processing_times_by_type(ProcessingType.SUMMARIZATION)
        
        # Calculate quality scores
        quality_scores = self._calculate_quality_scores(week_rates, transcription_times, summarization_times)
        
        # Analyze quality trends
        quality_trend = self._analyze_quality_trend(week_rates, month_rates)
        
        return {
            "assessment_period": "last_week",
            "quality_scores": quality_scores,
            "processing_reliability": {
                "transcription": {
                    "success_rate": week_rates["transcription"]["success_rate"],
                    "average_time": transcription_times["avg_seconds"],
                    "consistency_score": self._calculate_consistency_score(transcription_times)
                },
                "summarization": {
                    "success_rate": week_rates["summarization"]["success_rate"],
                    "average_time": summarization_times["avg_seconds"],
                    "consistency_score": self._calculate_consistency_score(summarization_times)
                }
            },
            "quality_trend": quality_trend,
            "improvement_areas": self._identify_improvement_areas(week_rates, transcription_times, summarization_times)
        }
    
    async def analyze_error_patterns(self) -> Dict[str, Any]:
        """
        Analyze error patterns and trends.
        
        Returns:
            Dictionary with error pattern analysis
        """
        # Get failure data
        week_rates = await self.analytics_repo.get_success_failure_rates(TimeRange.LAST_WEEK)
        month_rates = await self.analytics_repo.get_success_failure_rates(TimeRange.LAST_MONTH)
        
        # Analyze error patterns
        error_patterns = self._analyze_error_patterns(week_rates, month_rates)
        
        # Calculate error frequency and impact
        error_frequency = self._calculate_error_frequency(week_rates)
        error_impact = self._calculate_error_impact(week_rates)
        
        return {
            "analysis_period": "last_week_vs_month",
            "error_frequency": error_frequency,
            "error_impact": error_impact,
            "error_patterns": error_patterns,
            "error_trends": {
                "transcription_error_trend": self._calculate_error_trend(
                    week_rates["transcription"]["failed"],
                    month_rates["transcription"]["failed"]
                ),
                "summarization_error_trend": self._calculate_error_trend(
                    week_rates["summarization"]["failed"],
                    month_rates["summarization"]["failed"]
                )
            },
            "remediation_suggestions": self._generate_remediation_suggestions(error_patterns)
        }
    
    async def get_accuracy_metrics(self, processing_type: ProcessingType) -> Dict[str, Any]:
        """
        Get accuracy metrics for specific processing type.
        
        Args:
            processing_type: Type of processing to analyze
            
        Returns:
            Dictionary with accuracy metrics
        """
        # Get processing times and success rates
        processing_times = await self.analytics_repo.get_processing_times_by_type(processing_type)
        week_rates = await self.analytics_repo.get_success_failure_rates(TimeRange.LAST_WEEK)
        
        # Get relevant success rate for the processing type
        if processing_type == ProcessingType.TRANSCRIPTION:
            success_rate = week_rates["transcription"]["success_rate"]
            total_processed = week_rates["transcription"]["total"]
        elif processing_type == ProcessingType.SUMMARIZATION:
            success_rate = week_rates["summarization"]["success_rate"]
            total_processed = week_rates["summarization"]["total"]
        else:
            success_rate = 0.0
            total_processed = 0
        
        # Calculate accuracy metrics
        accuracy_score = self._calculate_accuracy_score(processing_type, success_rate, processing_times)
        
        return {
            "processing_type": processing_type.value,
            "accuracy_metrics": {
                "success_rate": success_rate,
                "total_processed": total_processed,
                "accuracy_score": accuracy_score,
                "reliability_index": self._calculate_reliability_index(success_rate, processing_times)
            },
            "performance_metrics": {
                "average_processing_time": processing_times["avg_seconds"],
                "min_processing_time": processing_times["min_seconds"],
                "max_processing_time": processing_times["max_seconds"],
                "time_consistency": self._calculate_time_consistency(processing_times)
            },
            "quality_indicators": {
                "speed_quality_ratio": self._calculate_speed_quality_ratio(success_rate, processing_times["avg_seconds"]),
                "processing_efficiency": self._calculate_processing_efficiency(processing_times, success_rate)
            },
            "benchmarks": self._get_quality_benchmarks(processing_type)
        }
    
    async def get_retry_success_rates(self) -> Dict[str, Any]:
        """
        Get retry success rates for failed operations.
        
        Returns:
            Dictionary with retry analysis
        """
        # This would require additional data about retry attempts
        # For now, provide a placeholder implementation with estimated data
        
        week_rates = await self.analytics_repo.get_success_failure_rates(TimeRange.LAST_WEEK)
        
        # Simulate retry data (in real implementation, this would come from retry logs)
        estimated_retry_data = self._simulate_retry_data(week_rates)
        
        return {
            "analysis_period": "last_week",
            "retry_statistics": estimated_retry_data,
            "retry_effectiveness": {
                "transcription_retry_success_rate": estimated_retry_data["transcription"]["retry_success_rate"],
                "summarization_retry_success_rate": estimated_retry_data["summarization"]["retry_success_rate"],
                "overall_retry_effectiveness": (
                    estimated_retry_data["transcription"]["retry_success_rate"] +
                    estimated_retry_data["summarization"]["retry_success_rate"]
                ) / 2
            },
            "retry_recommendations": self._generate_retry_recommendations(estimated_retry_data)
        }
    
    def _calculate_quality_scores(self, rates: Dict, transcription_times: Dict, summarization_times: Dict) -> Dict[str, float]:
        """Calculate overall quality scores."""
        # Quality score based on success rate and processing time consistency
        transcription_quality = (
            rates["transcription"]["success_rate"] * 0.7 +
            self._calculate_consistency_score(transcription_times) * 0.3
        )
        
        summarization_quality = (
            rates["summarization"]["success_rate"] * 0.7 +
            self._calculate_consistency_score(summarization_times) * 0.3
        )
        
        overall_quality = (transcription_quality + summarization_quality) / 2
        
        return {
            "transcription_quality_score": round(transcription_quality, 2),
            "summarization_quality_score": round(summarization_quality, 2),
            "overall_quality_score": round(overall_quality, 2)
        }
    
    def _calculate_consistency_score(self, processing_times: Dict) -> float:
        """Calculate consistency score based on processing time variance."""
        if processing_times["total_processed"] == 0:
            return 0.0
        
        avg_time = processing_times["avg_seconds"]
        min_time = processing_times["min_seconds"]
        max_time = processing_times["max_seconds"]
        
        if avg_time == 0:
            return 100.0
        
        # Calculate coefficient of variation (lower is better)
        time_range = max_time - min_time
        consistency = max(0, 100 - ((time_range / avg_time) * 100))
        
        return round(consistency, 2)
    
    def _analyze_quality_trend(self, week_rates: Dict, month_rates: Dict) -> Dict[str, Any]:
        """Analyze quality trends between week and month."""
        transcription_trend = week_rates["transcription"]["success_rate"] - month_rates["transcription"]["success_rate"]
        summarization_trend = week_rates["summarization"]["success_rate"] - month_rates["summarization"]["success_rate"]
        
        def get_trend_direction(trend_value: float) -> str:
            if trend_value > 2:
                return "improving"
            elif trend_value < -2:
                return "declining"
            else:
                return "stable"
        
        return {
            "transcription_trend": {
                "direction": get_trend_direction(transcription_trend),
                "change_percentage": round(transcription_trend, 2)
            },
            "summarization_trend": {
                "direction": get_trend_direction(summarization_trend),
                "change_percentage": round(summarization_trend, 2)
            },
            "overall_trend": get_trend_direction((transcription_trend + summarization_trend) / 2)
        }
    
    def _identify_improvement_areas(self, rates: Dict, transcription_times: Dict, summarization_times: Dict) -> List[str]:
        """Identify areas for quality improvement."""
        improvements = []
        
        if rates["transcription"]["success_rate"] < 90:
            improvements.append("Transcription service reliability needs improvement")
        
        if rates["summarization"]["success_rate"] < 90:
            improvements.append("Summarization service reliability needs improvement")
        
        if transcription_times["avg_seconds"] > 300:  # 5 minutes
            improvements.append("Transcription processing speed optimization needed")
        
        if summarization_times["avg_seconds"] > 120:  # 2 minutes
            improvements.append("Summarization processing speed optimization needed")
        
        transcription_consistency = self._calculate_consistency_score(transcription_times)
        if transcription_consistency < 70:
            improvements.append("Transcription processing time consistency needs improvement")
        
        summarization_consistency = self._calculate_consistency_score(summarization_times)
        if summarization_consistency < 70:
            improvements.append("Summarization processing time consistency needs improvement")
        
        return improvements
    
    def _analyze_error_patterns(self, week_rates: Dict, month_rates: Dict) -> List[Dict[str, Any]]:
        """Analyze patterns in errors."""
        patterns = []
        
        # Pattern: High failure rate
        if week_rates["transcription"]["failed"] > week_rates["transcription"]["total"] * 0.1:
            patterns.append({
                "pattern_type": "high_transcription_failure_rate",
                "severity": "high",
                "description": f"Transcription failure rate: {(week_rates['transcription']['failed'] / week_rates['transcription']['total'] * 100):.1f}%"
            })
        
        if week_rates["summarization"]["failed"] > week_rates["summarization"]["total"] * 0.1:
            patterns.append({
                "pattern_type": "high_summarization_failure_rate",
                "severity": "high",
                "description": f"Summarization failure rate: {(week_rates['summarization']['failed'] / week_rates['summarization']['total'] * 100):.1f}%"
            })
        
        # Pattern: Increasing failures
        transcription_increase = week_rates["transcription"]["failed"] - (month_rates["transcription"]["failed"] / 4)
        if transcription_increase > 5:
            patterns.append({
                "pattern_type": "increasing_transcription_failures",
                "severity": "medium",
                "description": "Transcription failures increasing compared to monthly average"
            })
        
        return patterns
    
    def _calculate_error_frequency(self, week_rates: Dict) -> Dict[str, Any]:
        """Calculate error frequency metrics."""
        total_operations = sum(
            week_rates[service]["total"] 
            for service in ["media", "transcription", "summarization"]
        )
        total_errors = sum(
            week_rates[service]["failed"] 
            for service in ["media", "transcription", "summarization"]
        )
        
        return {
            "total_operations": total_operations,
            "total_errors": total_errors,
            "overall_error_rate": (total_errors / total_operations * 100) if total_operations > 0 else 0,
            "errors_per_day": total_errors / 7,
            "error_distribution": {
                "media_errors": week_rates["media"]["failed"],
                "transcription_errors": week_rates["transcription"]["failed"],
                "summarization_errors": week_rates["summarization"]["failed"]
            }
        }
    
    def _calculate_error_impact(self, week_rates: Dict) -> Dict[str, Any]:
        """Calculate the impact of errors."""
        return {
            "processing_pipeline_impact": {
                "transcription_blocking_errors": week_rates["transcription"]["failed"],
                "summarization_blocking_errors": week_rates["summarization"]["failed"],
                "total_blocked_operations": week_rates["transcription"]["failed"] + week_rates["summarization"]["failed"]
            },
            "user_experience_impact": {
                "failed_media_processing": week_rates["media"]["failed"],
                "incomplete_workflows": week_rates["transcription"]["failed"] + week_rates["summarization"]["failed"]
            }
        }
    
    def _calculate_error_trend(self, week_errors: int, month_errors: int) -> str:
        """Calculate error trend direction."""
        monthly_avg = month_errors / 4  # Average per week
        
        if week_errors > monthly_avg * 1.2:
            return "increasing"
        elif week_errors < monthly_avg * 0.8:
            return "decreasing"
        else:
            return "stable"
    
    def _generate_remediation_suggestions(self, error_patterns: List[Dict]) -> List[str]:
        """Generate suggestions for error remediation."""
        suggestions = []
        
        for pattern in error_patterns:
            if pattern["pattern_type"] == "high_transcription_failure_rate":
                suggestions.append("Review transcription service configuration and error logs")
            elif pattern["pattern_type"] == "high_summarization_failure_rate":
                suggestions.append("Review summarization service configuration and model performance")
            elif pattern["pattern_type"] == "increasing_transcription_failures":
                suggestions.append("Monitor transcription service health and consider scaling")
        
        return suggestions
    
    def _calculate_accuracy_score(self, processing_type: ProcessingType, success_rate: float, processing_times: Dict) -> float:
        """Calculate accuracy score for processing type."""
        # Combine success rate with processing consistency
        consistency_score = self._calculate_consistency_score(processing_times)
        
        # Weight success rate heavily, consistency moderately
        accuracy_score = (success_rate * 0.8) + (consistency_score * 0.2)
        
        return round(accuracy_score, 2)
    
    def _calculate_reliability_index(self, success_rate: float, processing_times: Dict) -> float:
        """Calculate reliability index."""
        consistency = self._calculate_consistency_score(processing_times)
        
        # Reliability considers both success and predictability
        reliability = (success_rate * 0.6) + (consistency * 0.4)
        
        return round(reliability, 2)
    
    def _calculate_time_consistency(self, processing_times: Dict) -> str:
        """Calculate time consistency rating."""
        consistency_score = self._calculate_consistency_score(processing_times)
        
        if consistency_score >= 80:
            return "excellent"
        elif consistency_score >= 60:
            return "good"
        elif consistency_score >= 40:
            return "fair"
        else:
            return "poor"
    
    def _calculate_speed_quality_ratio(self, success_rate: float, avg_time: float) -> float:
        """Calculate speed vs quality ratio."""
        if avg_time == 0:
            return 0.0
        
        # Higher success rate and lower time = better ratio
        ratio = success_rate / avg_time * 10  # Scale factor
        
        return round(min(100, ratio), 2)
    
    def _calculate_processing_efficiency(self, processing_times: Dict, success_rate: float) -> float:
        """Calculate processing efficiency."""
        if processing_times["avg_seconds"] == 0:
            return 0.0
        
        # Efficiency = successful operations per second
        efficiency = success_rate / processing_times["avg_seconds"]
        
        return round(efficiency, 4)
    
    def _get_quality_benchmarks(self, processing_type: ProcessingType) -> Dict[str, Any]:
        """Get quality benchmarks for comparison."""
        if processing_type == ProcessingType.TRANSCRIPTION:
            return {
                "target_success_rate": 95.0,
                "target_avg_time": 180.0,  # 3 minutes
                "target_consistency": 80.0
            }
        elif processing_type == ProcessingType.SUMMARIZATION:
            return {
                "target_success_rate": 90.0,
                "target_avg_time": 60.0,   # 1 minute
                "target_consistency": 85.0
            }
        else:
            return {
                "target_success_rate": 90.0,
                "target_avg_time": 120.0,
                "target_consistency": 75.0
            }
    
    def _simulate_retry_data(self, week_rates: Dict) -> Dict[str, Any]:
        """Simulate retry data (placeholder for real retry tracking)."""
        return {
            "transcription": {
                "initial_failures": week_rates["transcription"]["failed"],
                "retry_attempts": int(week_rates["transcription"]["failed"] * 0.8),  # 80% retry rate
                "retry_successes": int(week_rates["transcription"]["failed"] * 0.6),  # 60% retry success
                "retry_success_rate": 75.0
            },
            "summarization": {
                "initial_failures": week_rates["summarization"]["failed"],
                "retry_attempts": int(week_rates["summarization"]["failed"] * 0.7),  # 70% retry rate
                "retry_successes": int(week_rates["summarization"]["failed"] * 0.5),  # 50% retry success
                "retry_success_rate": 71.4
            }
        }
    
    def _generate_retry_recommendations(self, retry_data: Dict) -> List[str]:
        """Generate recommendations for retry strategy."""
        recommendations = []
        
        if retry_data["transcription"]["retry_success_rate"] < 70:
            recommendations.append("Improve transcription retry logic and error handling")
        
        if retry_data["summarization"]["retry_success_rate"] < 70:
            recommendations.append("Improve summarization retry logic and error handling")
        
        return recommendations