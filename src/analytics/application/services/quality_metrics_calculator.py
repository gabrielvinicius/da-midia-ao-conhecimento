# src/analytics/application/services/quality_metrics_calculator.py
"""
Quality Metrics Calculator Service - Single Responsibility Principle
Extracted from QualityAnalytics God Class (462 lines)
Handles calculation of quality scores and metrics
"""

from typing import Dict, List, Any
from datetime import datetime
import structlog

from src.analytics.domain.interfaces import ProcessingType

logger = structlog.get_logger(__name__)


class QualityMetricsCalculator:
    """
    Quality metrics calculation with Single Responsibility:
    Calculate quality scores, consistency metrics, and performance ratios
    """
    
    def __init__(self):
        self.quality_thresholds = {
            "excellent_success_rate": 95.0,
            "good_success_rate": 90.0,
            "fair_success_rate": 80.0,
            "excellent_consistency": 80.0,
            "good_consistency": 60.0,
            "fair_consistency": 40.0
        }
    
    def calculate_quality_scores(
        self, 
        week_rates: Dict[str, Any], 
        transcription_times: Dict[str, Any], 
        summarization_times: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate comprehensive quality scores"""
        
        transcription_quality = self._calculate_service_quality_score(
            week_rates["transcription"]["success_rate"],
            transcription_times
        )
        
        summarization_quality = self._calculate_service_quality_score(
            week_rates["summarization"]["success_rate"],
            summarization_times
        )
        
        overall_quality = (transcription_quality + summarization_quality) / 2
        
        return {
            "transcription_quality": transcription_quality,
            "summarization_quality": summarization_quality,
            "overall_quality": round(overall_quality, 2),
            "quality_grade": self._get_quality_grade(overall_quality)
        }
    
    def calculate_consistency_score(self, processing_times: Dict[str, Any]) -> float:
        """Calculate consistency score based on processing time variance"""
        
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
    
    def calculate_speed_quality_ratio(self, success_rate: float, avg_time: float) -> float:
        """Calculate speed vs quality ratio"""
        
        if avg_time == 0:
            return 0.0
        
        # Higher success rate and lower time = better ratio
        ratio = success_rate / avg_time * 10  # Scale factor
        
        return round(min(100, ratio), 2)
    
    def calculate_processing_efficiency(self, processing_times: Dict[str, Any], success_rate: float) -> float:
        """Calculate processing efficiency"""
        
        if processing_times["avg_seconds"] == 0:
            return 0.0
        
        # Efficiency = successful operations per second
        efficiency = success_rate / processing_times["avg_seconds"]
        
        return round(efficiency, 4)
    
    def _calculate_service_quality_score(self, success_rate: float, processing_times: Dict[str, Any]) -> float:
        """Calculate quality score for a specific service"""
        
        # Success rate component (60% weight)
        success_component = success_rate * 0.6
        
        # Consistency component (25% weight)
        consistency_score = self.calculate_consistency_score(processing_times)
        consistency_component = consistency_score * 0.25
        
        # Speed component (15% weight)
        speed_score = self._calculate_speed_score(processing_times["avg_seconds"])
        speed_component = speed_score * 0.15
        
        total_score = success_component + consistency_component + speed_component
        
        return round(total_score, 2)
    
    def _calculate_speed_score(self, avg_time: float) -> float:
        """Calculate speed score based on average processing time"""
        
        # Speed thresholds (in seconds)
        excellent_time = 60
        good_time = 180
        fair_time = 300
        
        if avg_time <= excellent_time:
            return 100.0
        elif avg_time <= good_time:
            return 85.0
        elif avg_time <= fair_time:
            return 70.0
        else:
            return 50.0
    
    def _get_quality_grade(self, quality_score: float) -> str:
        """Get quality grade based on score"""
        
        if quality_score >= 90:
            return "A"
        elif quality_score >= 80:
            return "B"
        elif quality_score >= 70:
            return "C"
        elif quality_score >= 60:
            return "D"
        else:
            return "F"
    
    def get_time_consistency_rating(self, processing_times: Dict[str, Any]) -> str:
        """Get time consistency rating"""
        
        consistency_score = self.calculate_consistency_score(processing_times)
        
        if consistency_score >= self.quality_thresholds["excellent_consistency"]:
            return "excellent"
        elif consistency_score >= self.quality_thresholds["good_consistency"]:
            return "good"
        elif consistency_score >= self.quality_thresholds["fair_consistency"]:
            return "fair"
        else:
            return "poor"
    
    def get_quality_benchmarks(self, processing_type: ProcessingType) -> Dict[str, Any]:
        """Get quality benchmarks for comparison"""
        
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
    
    def calculate_benchmark_comparison(
        self, 
        actual_metrics: Dict[str, Any], 
        benchmark: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare actual metrics against benchmarks"""
        
        success_rate_diff = actual_metrics["success_rate"] - benchmark["target_success_rate"]
        time_diff = benchmark["target_avg_time"] - actual_metrics["avg_time"]  # Lower is better
        consistency_diff = actual_metrics["consistency"] - benchmark["target_consistency"]
        
        return {
            "success_rate_comparison": {
                "difference": round(success_rate_diff, 2),
                "status": "above_target" if success_rate_diff >= 0 else "below_target"
            },
            "time_comparison": {
                "difference": round(time_diff, 2),
                "status": "better_than_target" if time_diff >= 0 else "slower_than_target"
            },
            "consistency_comparison": {
                "difference": round(consistency_diff, 2),
                "status": "above_target" if consistency_diff >= 0 else "below_target"
            }
        }
    
    def get_metrics_summary(self, quality_scores: Dict[str, Any]) -> Dict[str, Any]:
        """Get summary of quality metrics"""
        
        return {
            "overall_grade": quality_scores["quality_grade"],
            "overall_score": quality_scores["overall_quality"],
            "performance_summary": {
                "transcription": {
                    "score": quality_scores["transcription_quality"],
                    "grade": self._get_quality_grade(quality_scores["transcription_quality"])
                },
                "summarization": {
                    "score": quality_scores["summarization_quality"],
                    "grade": self._get_quality_grade(quality_scores["summarization_quality"])
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        }


# Default instance
quality_metrics_calculator = QualityMetricsCalculator()