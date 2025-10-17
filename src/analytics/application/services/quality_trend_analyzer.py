# src/analytics/application/services/quality_trend_analyzer.py
"""
Quality Trend Analyzer Service - Single Responsibility Principle
Extracted from QualityAnalytics God Class (462 lines)
Handles trend analysis and pattern detection
"""

from typing import Dict, List, Any
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger(__name__)


class QualityTrendAnalyzer:
    """
    Quality trend analysis with Single Responsibility:
    Analyze trends, patterns, and provide improvement recommendations
    """
    
    def __init__(self):
        self.trend_thresholds = {
            "significant_improvement": 2.0,
            "significant_decline": -2.0,
            "stable_range": 2.0
        }
    
    def analyze_quality_trend(self, week_rates: Dict[str, Any], month_rates: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze quality trends between week and month"""
        
        transcription_trend = week_rates["transcription"]["success_rate"] - month_rates["transcription"]["success_rate"]
        summarization_trend = week_rates["summarization"]["success_rate"] - month_rates["summarization"]["success_rate"]
        
        return {
            "transcription_trend": {
                "direction": self._get_trend_direction(transcription_trend),
                "change_percentage": round(transcription_trend, 2),
                "interpretation": self._interpret_trend(transcription_trend, "transcription")
            },
            "summarization_trend": {
                "direction": self._get_trend_direction(summarization_trend),
                "change_percentage": round(summarization_trend, 2),
                "interpretation": self._interpret_trend(summarization_trend, "summarization")
            },
            "overall_trend": self._get_trend_direction((transcription_trend + summarization_trend) / 2),
            "trend_summary": self._generate_trend_summary(transcription_trend, summarization_trend)
        }
    
    def analyze_error_patterns(self, week_rates: Dict[str, Any], month_rates: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze error patterns and trends"""
        
        # Calculate error rate trends
        transcription_error_trend = self._calculate_error_rate_trend(
            week_rates["transcription"], month_rates["transcription"]
        )
        
        summarization_error_trend = self._calculate_error_rate_trend(
            week_rates["summarization"], month_rates["summarization"]
        )
        
        # Analyze error frequency patterns
        error_frequency = self._analyze_error_frequency(week_rates)
        
        # Identify critical error patterns
        critical_patterns = self._identify_critical_error_patterns(week_rates, month_rates)
        
        return {
            "error_trends": {
                "transcription": transcription_error_trend,
                "summarization": summarization_error_trend
            },
            "error_frequency": error_frequency,
            "critical_patterns": critical_patterns,
            "error_impact_assessment": self._assess_error_impact(week_rates),
            "error_recommendations": self._generate_error_recommendations(critical_patterns)
        }
    
    def identify_improvement_areas(
        self, 
        rates: Dict[str, Any], 
        transcription_times: Dict[str, Any], 
        summarization_times: Dict[str, Any]
    ) -> List[str]:
        """Identify areas for quality improvement"""
        
        improvements = []
        
        # Success rate improvements
        if rates["transcription"]["success_rate"] < 90:
            improvements.append("Transcription service reliability needs improvement")
        
        if rates["summarization"]["success_rate"] < 90:
            improvements.append("Summarization service reliability needs improvement")
        
        # Performance improvements
        if transcription_times["avg_seconds"] > 300:  # 5 minutes
            improvements.append("Transcription processing speed optimization needed")
        
        if summarization_times["avg_seconds"] > 120:  # 2 minutes
            improvements.append("Summarization processing speed optimization needed")
        
        # Consistency improvements
        from .quality_metrics_calculator import quality_metrics_calculator
        
        transcription_consistency = quality_metrics_calculator.calculate_consistency_score(transcription_times)
        if transcription_consistency < 60:
            improvements.append("Transcription processing consistency needs improvement")
        
        summarization_consistency = quality_metrics_calculator.calculate_consistency_score(summarization_times)
        if summarization_consistency < 60:
            improvements.append("Summarization processing consistency needs improvement")
        
        return improvements
    
    def analyze_retry_effectiveness(self, week_rates: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze retry strategy effectiveness"""
        
        # Simulate retry data (in production, this would come from actual metrics)
        retry_data = self._simulate_retry_data(week_rates)
        
        # Analyze retry patterns
        retry_analysis = self._analyze_retry_patterns(retry_data)
        
        # Generate retry recommendations
        retry_recommendations = self._generate_retry_recommendations(retry_data)
        
        return {
            "retry_data": retry_data,
            "retry_analysis": retry_analysis,
            "retry_effectiveness": self._calculate_retry_effectiveness(retry_data),
            "recommendations": retry_recommendations
        }
    
    def _get_trend_direction(self, trend_value: float) -> str:
        """Get trend direction based on threshold"""
        
        if trend_value > self.trend_thresholds["significant_improvement"]:
            return "improving"
        elif trend_value < self.trend_thresholds["significant_decline"]:
            return "declining"
        else:
            return "stable"
    
    def _interpret_trend(self, trend_value: float, service_type: str) -> str:
        """Interpret trend value with context"""
        
        direction = self._get_trend_direction(trend_value)
        
        if direction == "improving":
            return f"{service_type.title()} quality is improving significantly (+{trend_value:.1f}%)"
        elif direction == "declining":
            return f"{service_type.title()} quality is declining (-{abs(trend_value):.1f}%)"
        else:
            return f"{service_type.title()} quality is stable (±{abs(trend_value):.1f}%)"
    
    def _generate_trend_summary(self, transcription_trend: float, summarization_trend: float) -> str:
        """Generate overall trend summary"""
        
        avg_trend = (transcription_trend + summarization_trend) / 2
        
        if avg_trend > 2:
            return "Overall system quality is improving across services"
        elif avg_trend < -2:
            return "Overall system quality is declining and needs attention"
        else:
            return "Overall system quality is stable with minor fluctuations"
    
    def _calculate_error_rate_trend(self, week_data: Dict[str, Any], month_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate error rate trend for a service"""
        
        week_error_rate = (week_data["failed"] / max(week_data["total"], 1)) * 100
        month_error_rate = (month_data["failed"] / max(month_data["total"], 1)) * 100
        
        error_trend = week_error_rate - month_error_rate
        
        return {
            "week_error_rate": round(week_error_rate, 2),
            "month_error_rate": round(month_error_rate, 2),
            "trend_change": round(error_trend, 2),
            "trend_direction": "increasing" if error_trend > 0 else "decreasing" if error_trend < 0 else "stable"
        }
    
    def _analyze_error_frequency(self, week_rates: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze error frequency patterns"""
        
        total_errors = week_rates["transcription"]["failed"] + week_rates["summarization"]["failed"]
        total_requests = week_rates["transcription"]["total"] + week_rates["summarization"]["total"]
        
        return {
            "total_errors": total_errors,
            "total_requests": total_requests,
            "overall_error_rate": round((total_errors / max(total_requests, 1)) * 100, 2),
            "transcription_error_contribution": round((week_rates["transcription"]["failed"] / max(total_errors, 1)) * 100, 2),
            "summarization_error_contribution": round((week_rates["summarization"]["failed"] / max(total_errors, 1)) * 100, 2)
        }
    
    def _identify_critical_error_patterns(self, week_rates: Dict[str, Any], month_rates: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify critical error patterns"""
        
        patterns = []
        
        # High error rate pattern
        for service in ["transcription", "summarization"]:
            week_error_rate = (week_rates[service]["failed"] / max(week_rates[service]["total"], 1)) * 100
            
            if week_error_rate > 10:  # More than 10% error rate
                patterns.append({
                    "pattern_type": "high_error_rate",
                    "service": service,
                    "error_rate": week_error_rate,
                    "severity": "critical" if week_error_rate > 20 else "high"
                })
        
        # Increasing error trend pattern
        for service in ["transcription", "summarization"]:
            week_errors = week_rates[service]["failed"]
            month_errors = month_rates[service]["failed"]
            
            if week_errors > month_errors * 1.5:  # 50% increase in errors
                patterns.append({
                    "pattern_type": "increasing_errors",
                    "service": service,
                    "increase_factor": round(week_errors / max(month_errors, 1), 2),
                    "severity": "high"
                })
        
        return patterns
    
    def _assess_error_impact(self, week_rates: Dict[str, Any]) -> Dict[str, Any]:
        """Assess the impact of errors on system performance"""
        
        total_failed = week_rates["transcription"]["failed"] + week_rates["summarization"]["failed"]
        total_requests = week_rates["transcription"]["total"] + week_rates["summarization"]["total"]
        
        impact_level = "low"
        if total_failed > total_requests * 0.15:  # More than 15% failure rate
            impact_level = "critical"
        elif total_failed > total_requests * 0.10:  # More than 10% failure rate
            impact_level = "high"
        elif total_failed > total_requests * 0.05:  # More than 5% failure rate
            impact_level = "medium"
        
        return {
            "impact_level": impact_level,
            "affected_requests": total_failed,
            "total_requests": total_requests,
            "impact_percentage": round((total_failed / max(total_requests, 1)) * 100, 2)
        }
    
    def _generate_error_recommendations(self, critical_patterns: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on error patterns"""
        
        recommendations = []
        
        for pattern in critical_patterns:
            if pattern["pattern_type"] == "high_error_rate":
                recommendations.append(
                    f"Immediate investigation needed for {pattern['service']} service "
                    f"(error rate: {pattern['error_rate']:.1f}%)"
                )
            elif pattern["pattern_type"] == "increasing_errors":
                recommendations.append(
                    f"Monitor {pattern['service']} service closely "
                    f"(errors increased by {pattern['increase_factor']}x)"
                )
        
        if not recommendations:
            recommendations.append("Continue monitoring error patterns for early detection")
        
        return recommendations
    
    def _simulate_retry_data(self, week_rates: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate retry data (placeholder for real retry tracking)"""
        
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
    
    def _analyze_retry_patterns(self, retry_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze retry patterns"""
        
        total_retries = sum(data["retry_attempts"] for data in retry_data.values())
        total_retry_successes = sum(data["retry_successes"] for data in retry_data.values())
        
        overall_retry_success_rate = (total_retry_successes / max(total_retries, 1)) * 100
        
        return {
            "total_retry_attempts": total_retries,
            "total_retry_successes": total_retry_successes,
            "overall_retry_success_rate": round(overall_retry_success_rate, 2),
            "service_retry_performance": {
                service: {
                    "retry_rate": round((data["retry_attempts"] / max(data["initial_failures"], 1)) * 100, 2),
                    "success_rate": data["retry_success_rate"]
                }
                for service, data in retry_data.items()
            }
        }
    
    def _calculate_retry_effectiveness(self, retry_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate retry strategy effectiveness"""
        
        total_initial_failures = sum(data["initial_failures"] for data in retry_data.values())
        total_final_successes = sum(data["retry_successes"] for data in retry_data.values())
        
        recovery_rate = (total_final_successes / max(total_initial_failures, 1)) * 100
        
        effectiveness = "high" if recovery_rate > 60 else "medium" if recovery_rate > 40 else "low"
        
        return {
            "recovery_rate": round(recovery_rate, 2),
            "effectiveness": effectiveness,
            "total_recovered_requests": total_final_successes
        }
    
    def _generate_retry_recommendations(self, retry_data: Dict[str, Any]) -> List[str]:
        """Generate recommendations for retry strategy"""
        
        recommendations = []
        
        for service, data in retry_data.items():
            if data["retry_success_rate"] < 70:
                recommendations.append(f"Improve {service} retry logic and error handling")
        
        if not recommendations:
            recommendations.append("Retry strategies are performing well")
        
        return recommendations


# Default instance
quality_trend_analyzer = QualityTrendAnalyzer()