"""
Enhanced Analytics Service - Single Responsibility: Orchestrate comprehensive analytics.
Follows SOLID principles by coordinating specialized analytics services.
"""
from typing import Dict, Any
from datetime import datetime
import structlog

from src.analytics.domain.interfaces import (
    IEnhancedAnalyticsService, 
    IPerformanceAnalytics, 
    IQualityAnalytics,
    IAnalyticsAggregator,
    IAnalyticsValidator,
    TimeRange
)

logger = structlog.get_logger(__name__)


class EnhancedAnalyticsService(IEnhancedAnalyticsService):
    """
    Enhanced analytics service following SOLID principles.
    
    Single Responsibility: Orchestrate comprehensive analytics workflow.
    Open/Closed: Extensible through service injection.
    Liskov Substitution: Implements IEnhancedAnalyticsService contract.
    Interface Segregation: Uses specific interfaces for each concern.
    Dependency Inversion: Depends on abstractions, not concretions.
    """
    
    def __init__(
        self,
        performance_analytics: IPerformanceAnalytics,
        quality_analytics: IQualityAnalytics,
        aggregator: IAnalyticsAggregator,
        validator: IAnalyticsValidator
    ):
        self._performance_analytics = performance_analytics
        self._quality_analytics = quality_analytics
        self._aggregator = aggregator
        self._validator = validator
    
    async def get_comprehensive_analytics(self, time_range: TimeRange) -> Dict[str, Any]:
        """
        Get comprehensive analytics combining all metrics.
        
        Args:
            time_range: Time range for analysis
            
        Returns:
            Dict with comprehensive analytics data
        """
        self._validator.validate_time_range(time_range)
        
        try:
            # Get analytics from specialized services
            performance_data = await self._aggregator.aggregate_performance_data(time_range)
            quality_data = await self._aggregator.aggregate_quality_data(time_range)
            user_data = await self._aggregator.aggregate_user_metrics(time_range)
            
            # Get detailed analytics
            throughput_metrics = await self._performance_analytics.calculate_throughput_metrics(time_range)
            bottleneck_analysis = await self._performance_analytics.analyze_bottlenecks()
            quality_metrics = await self._quality_analytics.get_processing_quality_metrics()
            
            # Combine all analytics
            comprehensive_data = {
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "time_range": time_range.value,
                "summary": self._generate_executive_summary(performance_data, quality_data, user_data),
                "performance": {
                    "aggregated_data": performance_data,
                    "throughput_analysis": throughput_metrics,
                    "bottleneck_analysis": bottleneck_analysis
                },
                "quality": {
                    "aggregated_data": quality_data,
                    "detailed_metrics": quality_metrics
                },
                "user_analytics": user_data,
                "insights": await self._generate_insights_internal(time_range),
                "recommendations": self._generate_recommendations(bottleneck_analysis, quality_metrics)
            }
            
            logger.info(
                "analytics.comprehensive.completed",
                time_range=time_range.value,
                data_points_analyzed=len(comprehensive_data)
            )
            
            return comprehensive_data
            
        except Exception as e:
            logger.error(
                "analytics.comprehensive.failed",
                time_range=time_range.value,
                error=str(e)
            )
            raise
    
    async def get_real_time_dashboard(self) -> Dict[str, Any]:
        """
        Get real-time dashboard metrics.
        
        Returns:
            Dict with real-time dashboard data
        """
        try:
            # Get current hour data for real-time metrics
            current_performance = await self._aggregator.aggregate_performance_data(TimeRange.LAST_HOUR)
            current_quality = await self._aggregator.aggregate_quality_data(TimeRange.LAST_HOUR)
            
            # Get resource utilization
            resource_utilization = await self._performance_analytics.get_resource_utilization()
            
            # Generate real-time dashboard
            dashboard_data = {
                "dashboard_timestamp": datetime.utcnow().isoformat(),
                "system_status": self._determine_system_status(current_performance, current_quality),
                "current_performance": {
                    "overall_success_rate": current_performance["system_health"]["overall_success_rate"],
                    "operations_per_hour": current_performance["throughput_metrics"]["operations_per_hour"],
                    "health_status": current_performance["system_health"]["health_status"]
                },
                "current_quality": {
                    "quality_score": current_quality["quality_scores"]["overall_quality"],
                    "reliability_status": self._assess_reliability(current_quality)
                },
                "resource_utilization": resource_utilization["estimated_resource_usage"],
                "active_alerts": await self._get_active_alerts(current_performance, current_quality),
                "quick_stats": self._generate_quick_stats(current_performance, current_quality)
            }
            
            logger.info("analytics.dashboard.generated")
            
            return dashboard_data
            
        except Exception as e:
            logger.error(
                "analytics.dashboard.failed",
                error=str(e)
            )
            raise
    
    async def generate_insights(self, time_range: TimeRange) -> Dict[str, Any]:
        """
        Generate actionable insights from analytics data.
        
        Args:
            time_range: Time range for analysis
            
        Returns:
            Dict with actionable insights
        """
        return await self._generate_insights_internal(time_range)
    
    async def _generate_insights_internal(self, time_range: TimeRange) -> Dict[str, Any]:
        """Internal method to generate insights."""
        self._validator.validate_time_range(time_range)
        
        try:
            # Get analytics data for insights
            bottlenecks = await self._performance_analytics.analyze_bottlenecks()
            quality_metrics = await self._quality_analytics.get_processing_quality_metrics()
            error_patterns = await self._quality_analytics.analyze_error_patterns()
            load_prediction = await self._performance_analytics.predict_processing_load(24)
            
            insights = {
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "time_range": time_range.value,
                "performance_insights": self._extract_performance_insights(bottlenecks, load_prediction),
                "quality_insights": self._extract_quality_insights(quality_metrics, error_patterns),
                "operational_insights": self._extract_operational_insights(bottlenecks, quality_metrics),
                "strategic_recommendations": self._generate_strategic_recommendations(
                    bottlenecks, quality_metrics, error_patterns
                ),
                "priority_actions": self._identify_priority_actions(bottlenecks, error_patterns)
            }
            
            logger.info(
                "analytics.insights.generated",
                time_range=time_range.value,
                insights_count=len(insights["priority_actions"])
            )
            
            return insights
            
        except Exception as e:
            logger.error(
                "analytics.insights.failed",
                time_range=time_range.value,
                error=str(e)
            )
            raise
    
    def _generate_executive_summary(
        self, 
        performance_data: Dict[str, Any], 
        quality_data: Dict[str, Any], 
        user_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate executive summary from analytics data."""
        return {
            "overall_health": performance_data["system_health"]["health_status"],
            "success_rate": performance_data["system_health"]["overall_success_rate"],
            "quality_score": quality_data["quality_scores"]["overall_quality"],
            "total_operations": performance_data["throughput_metrics"]["total_operations"],
            "active_users": user_data["user_activity"]["total_active_users"],
            "key_metrics": {
                "operations_per_hour": performance_data["throughput_metrics"]["operations_per_hour"],
                "user_engagement": user_data["user_activity"]["engagement_level"],
                "system_efficiency": self._calculate_system_efficiency(performance_data, quality_data)
            }
        }
    
    def _determine_system_status(self, performance_data: Dict, quality_data: Dict) -> str:
        """Determine overall system status."""
        health_status = performance_data["system_health"]["health_status"]
        quality_score = quality_data["quality_scores"]["overall_quality"]
        
        if health_status == "excellent" and quality_score >= 90:
            return "optimal"
        elif health_status in ["excellent", "good"] and quality_score >= 80:
            return "healthy"
        elif health_status == "fair" or quality_score >= 70:
            return "warning"
        else:
            return "critical"
    
    def _assess_reliability(self, quality_data: Dict) -> str:
        """Assess system reliability status."""
        overall_quality = quality_data["quality_scores"]["overall_quality"]
        
        if overall_quality >= 95:
            return "excellent"
        elif overall_quality >= 85:
            return "good"
        elif overall_quality >= 70:
            return "fair"
        else:
            return "poor"
    
    async def _get_active_alerts(self, performance_data: Dict, quality_data: Dict) -> list:
        """Get active system alerts."""
        alerts = []
        
        # Performance alerts
        if performance_data["system_health"]["health_status"] == "poor":
            alerts.append({
                "type": "performance",
                "severity": "high",
                "message": "System performance is below acceptable levels"
            })
        
        # Quality alerts
        if quality_data["quality_scores"]["overall_quality"] < 70:
            alerts.append({
                "type": "quality",
                "severity": "medium",
                "message": "Processing quality has declined"
            })
        
        return alerts
    
    def _generate_quick_stats(self, performance_data: Dict, quality_data: Dict) -> Dict[str, Any]:
        """Generate quick statistics for dashboard."""
        return {
            "uptime_percentage": 99.5,  # Placeholder - would calculate from actual uptime data
            "avg_response_time": "2.3s",  # Placeholder
            "total_processed_today": performance_data["throughput_metrics"]["total_operations"],
            "error_rate": 100 - performance_data["system_health"]["overall_success_rate"]
        }
    
    def _extract_performance_insights(self, bottlenecks: Dict, load_prediction: Dict) -> list:
        """Extract performance insights."""
        insights = []
        
        if bottlenecks["bottleneck_score"] > 5:
            insights.append({
                "category": "performance",
                "insight": "Multiple performance bottlenecks detected",
                "impact": "high",
                "recommendation": "Immediate optimization required"
            })
        
        peak_load = load_prediction["summary"]["peak_load"]
        if peak_load > 50:
            insights.append({
                "category": "capacity",
                "insight": f"High load predicted: {peak_load} operations/hour",
                "impact": "medium",
                "recommendation": "Consider scaling resources proactively"
            })
        
        return insights
    
    def _extract_quality_insights(self, quality_metrics: Dict, error_patterns: Dict) -> list:
        """Extract quality insights."""
        insights = []
        
        if quality_metrics["quality_scores"]["overall_quality_score"] < 80:
            insights.append({
                "category": "quality",
                "insight": "Processing quality below target threshold",
                "impact": "medium",
                "recommendation": "Review and optimize processing algorithms"
            })
        
        if error_patterns["retry_effectiveness"]["overall_retry_effectiveness"] < 70:
            insights.append({
                "category": "reliability",
                "insight": "Retry mechanisms are not effective",
                "impact": "medium",
                "recommendation": "Enhance error handling and retry logic"
            })
        
        return insights
    
    def _calculate_system_efficiency(self, performance_data: Dict, quality_data: Dict) -> float:
        """Calculate overall system efficiency score."""
        success_rate = performance_data["system_health"]["overall_success_rate"]
        quality_score = quality_data["quality_scores"]["overall_quality"]
        
        # Weighted efficiency score
        efficiency = (success_rate * 0.6) + (quality_score * 0.4)
        return round(efficiency, 2)