# src/analytics/application/services/simplified_quality_analytics.py
"""
Simplified Quality Analytics - Replacement for 462-line God Class
Composes the broken-down components following Single Responsibility Principle
"""

from typing import Dict, List, Any
from datetime import datetime
import structlog

from src.analytics.domain.interfaces import IQualityAnalytics, IAnalyticsRepository, ProcessingType, TimeRange
from .quality_metrics_calculator import QualityMetricsCalculator, quality_metrics_calculator
from .quality_trend_analyzer import QualityTrendAnalyzer, quality_trend_analyzer

logger = structlog.get_logger(__name__)


class SimplifiedQualityAnalytics(IQualityAnalytics):
    """
    Simplified Quality Analytics following SOLID principles
    
    Replaces the original 462-line QualityAnalytics God Class with composition of focused components:
    - QualityMetricsCalculator: Quality score calculations and benchmarking
    - QualityTrendAnalyzer: Trend analysis and pattern detection
    
    This class provides the same interface but with much better separation of concerns.
    """
    
    def __init__(self, analytics_repo: IAnalyticsRepository):
        self.analytics_repo = analytics_repo
        self.metrics_calculator = quality_metrics_calculator
        self.trend_analyzer = quality_trend_analyzer
        
        logger.info("Initialized simplified quality analytics with SOLID architecture")
    
    async def get_processing_quality_metrics(self) -> Dict[str, Any]:
        """
        Get processing quality metrics using specialized components
        """
        try:
            # Get data from repository
            week_rates = await self.analytics_repo.get_success_failure_rates(TimeRange.LAST_WEEK)
            month_rates = await self.analytics_repo.get_success_failure_rates(TimeRange.LAST_MONTH)
            transcription_times = await self.analytics_repo.get_processing_times_by_type(ProcessingType.TRANSCRIPTION)
            summarization_times = await self.analytics_repo.get_processing_times_by_type(ProcessingType.SUMMARIZATION)
            
            # Calculate quality scores using specialized calculator
            quality_scores = self.metrics_calculator.calculate_quality_scores(
                week_rates, transcription_times, summarization_times
            )
            
            # Analyze trends using specialized analyzer
            quality_trend = self.trend_analyzer.analyze_quality_trend(week_rates, month_rates)
            
            # Identify improvement areas
            improvement_areas = self.trend_analyzer.identify_improvement_areas(
                week_rates, transcription_times, summarization_times
            )
            
            return {
                "assessment_period": "last_week",
                "quality_scores": quality_scores,
                "processing_reliability": {
                    "transcription": {
                        "success_rate": week_rates["transcription"]["success_rate"],
                        "average_time": transcription_times["avg_seconds"],
                        "consistency_score": self.metrics_calculator.calculate_consistency_score(transcription_times),
                        "consistency_rating": self.metrics_calculator.get_time_consistency_rating(transcription_times)
                    },
                    "summarization": {
                        "success_rate": week_rates["summarization"]["success_rate"],
                        "average_time": summarization_times["avg_seconds"],
                        "consistency_score": self.metrics_calculator.calculate_consistency_score(summarization_times),
                        "consistency_rating": self.metrics_calculator.get_time_consistency_rating(summarization_times)
                    }
                },
                "quality_trend": quality_trend,
                "improvement_areas": improvement_areas,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to get processing quality metrics", error=str(e))
            raise
    
    async def analyze_error_patterns(self) -> Dict[str, Any]:
        """
        Analyze error patterns using specialized trend analyzer
        """
        try:
            # Get failure data
            week_rates = await self.analytics_repo.get_success_failure_rates(TimeRange.LAST_WEEK)
            month_rates = await self.analytics_repo.get_success_failure_rates(TimeRange.LAST_MONTH)
            
            # Use specialized analyzer for error pattern analysis
            error_analysis = self.trend_analyzer.analyze_error_patterns(week_rates, month_rates)
            
            return {
                "analysis_period": "last_week_vs_month",
                **error_analysis,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to analyze error patterns", error=str(e))
            raise
    
    async def get_quality_benchmarks(self, processing_type: ProcessingType) -> Dict[str, Any]:
        """
        Get quality benchmarks using metrics calculator
        """
        try:
            benchmarks = self.metrics_calculator.get_quality_benchmarks(processing_type)
            
            # Get current metrics for comparison
            current_times = await self.analytics_repo.get_processing_times_by_type(processing_type)
            current_rates = await self.analytics_repo.get_success_failure_rates(TimeRange.LAST_WEEK)
            
            service_key = processing_type.value.lower()
            actual_metrics = {
                "success_rate": current_rates[service_key]["success_rate"],
                "avg_time": current_times["avg_seconds"],
                "consistency": self.metrics_calculator.calculate_consistency_score(current_times)
            }
            
            # Compare against benchmarks
            comparison = self.metrics_calculator.calculate_benchmark_comparison(actual_metrics, benchmarks)
            
            return {
                "processing_type": processing_type.value,
                "benchmarks": benchmarks,
                "current_metrics": actual_metrics,
                "comparison": comparison,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to get quality benchmarks", processing_type=processing_type.value, error=str(e))
            raise
    
    async def analyze_retry_effectiveness(self) -> Dict[str, Any]:
        """
        Analyze retry effectiveness using trend analyzer
        """
        try:
            week_rates = await self.analytics_repo.get_success_failure_rates(TimeRange.LAST_WEEK)
            
            # Use specialized analyzer for retry analysis
            retry_analysis = self.trend_analyzer.analyze_retry_effectiveness(week_rates)
            
            return {
                "analysis_period": "last_week",
                **retry_analysis,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to analyze retry effectiveness", error=str(e))
            raise
    
    async def get_comprehensive_quality_report(self) -> Dict[str, Any]:
        """
        Get comprehensive quality report combining all analytics
        """
        try:
            # Get all quality metrics
            quality_metrics = await self.get_processing_quality_metrics()
            error_patterns = await self.analyze_error_patterns()
            
            # Get benchmarks for both processing types
            transcription_benchmarks = await self.get_quality_benchmarks(ProcessingType.TRANSCRIPTION)
            summarization_benchmarks = await self.get_quality_benchmarks(ProcessingType.SUMMARIZATION)
            
            # Get retry analysis
            retry_analysis = await self.analyze_retry_effectiveness()
            
            # Generate summary
            summary = self.metrics_calculator.get_metrics_summary(quality_metrics["quality_scores"])
            
            return {
                "report_type": "comprehensive_quality_report",
                "generated_at": datetime.utcnow().isoformat(),
                "summary": summary,
                "quality_metrics": quality_metrics,
                "error_analysis": error_patterns,
                "benchmarks": {
                    "transcription": transcription_benchmarks,
                    "summarization": summarization_benchmarks
                },
                "retry_analysis": retry_analysis
            }
            
        except Exception as e:
            logger.error("Failed to generate comprehensive quality report", error=str(e))
            raise
    
    # === Component access methods for advanced usage ===
    
    def get_metrics_calculator(self) -> QualityMetricsCalculator:
        """Get the metrics calculator component"""
        return self.metrics_calculator
    
    def get_trend_analyzer(self) -> QualityTrendAnalyzer:
        """Get the trend analyzer component"""
        return self.trend_analyzer
    
    def get_analytics_info(self) -> Dict[str, Any]:
        """Get analytics service information"""
        return {
            "service_name": "SimplifiedQualityAnalytics",
            "architecture": "SOLID_components",
            "components": {
                "metrics_calculator": "QualityMetricsCalculator",
                "trend_analyzer": "QualityTrendAnalyzer"
            },
            "repository": type(self.analytics_repo).__name__
        }


# Backward compatibility - alias for the original class name
QualityAnalytics = SimplifiedQualityAnalytics