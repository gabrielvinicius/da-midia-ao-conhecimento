"""
Domain interfaces for analytics module.
Follows Dependency Inversion Principle (DIP).
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from uuid import UUID
from datetime import datetime
from enum import Enum


class ProcessingType(Enum):
    """Types of processing operations for analytics."""
    TRANSCRIPTION = "transcription"
    SUMMARIZATION = "summarization"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    TOPIC_MODELING = "topic_modeling"


class TimeRange(Enum):
    """Time ranges for analytics queries."""
    LAST_HOUR = "last_hour"
    LAST_DAY = "last_day"
    LAST_WEEK = "last_week"
    LAST_MONTH = "last_month"
    LAST_YEAR = "last_year"
    CUSTOM = "custom"


class IAnalyticsRepository(ABC):
    """Interface for analytics repository operations."""
    
    @abstractmethod
    async def get_average_processing_times(self) -> Dict[str, Any]:
        """Get average processing times for all operations."""
        pass
    
    @abstractmethod
    async def get_processing_times_by_type(self, processing_type: ProcessingType) -> Dict[str, Any]:
        """Get processing times for specific operation type."""
        pass
    
    @abstractmethod
    async def get_success_failure_rates(self, time_range: TimeRange) -> Dict[str, Any]:
        """Get success and failure rates for a given time range."""
        pass
    
    @abstractmethod
    async def get_user_activity_metrics(self, user_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Get user activity metrics."""
        pass
    
    @abstractmethod
    async def get_media_type_distribution(self) -> Dict[str, Any]:
        """Get distribution of media types processed."""
        pass


class IAnalyticsQueries(ABC):
    """Interface for analytics query operations."""
    
    @abstractmethod
    async def estimate_processing_time(self, content_metric: float) -> Dict[str, Any]:
        """Estimate processing time based on content metric."""
        pass
    
    @abstractmethod
    async def get_system_performance_metrics(self, time_range: TimeRange) -> Dict[str, Any]:
        """Get comprehensive system performance metrics."""
        pass
    
    @abstractmethod
    async def get_processing_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get processing trends over time."""
        pass
    
    @abstractmethod
    async def get_user_analytics(self, user_id: UUID) -> Dict[str, Any]:
        """Get analytics for specific user."""
        pass
    
    @abstractmethod
    async def get_media_analytics(self, media_id: UUID) -> Dict[str, Any]:
        """Get analytics for specific media item."""
        pass


class IPerformanceAnalytics(ABC):
    """Interface for performance analytics operations."""
    
    @abstractmethod
    async def calculate_throughput_metrics(self, time_range: TimeRange) -> Dict[str, Any]:
        """Calculate system throughput metrics."""
        pass
    
    @abstractmethod
    async def analyze_bottlenecks(self) -> Dict[str, Any]:
        """Identify system bottlenecks."""
        pass
    
    @abstractmethod
    async def get_resource_utilization(self) -> Dict[str, Any]:
        """Get resource utilization metrics."""
        pass
    
    @abstractmethod
    async def predict_processing_load(self, hours_ahead: int = 24) -> Dict[str, Any]:
        """Predict processing load for the next N hours."""
        pass


class IUsageAnalytics(ABC):
    """Interface for usage analytics operations."""
    
    @abstractmethod
    async def get_user_engagement_metrics(self, time_range: TimeRange) -> Dict[str, Any]:
        """Get user engagement metrics."""
        pass
    
    @abstractmethod
    async def get_feature_usage_stats(self) -> Dict[str, Any]:
        """Get feature usage statistics."""
        pass
    
    @abstractmethod
    async def get_most_active_users(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most active users."""
        pass
    
    @abstractmethod
    async def get_peak_usage_times(self) -> Dict[str, Any]:
        """Get peak usage times analysis."""
        pass


class IQualityAnalytics(ABC):
    """Interface for quality analytics operations."""
    
    @abstractmethod
    async def get_processing_quality_metrics(self) -> Dict[str, Any]:
        """Get processing quality metrics."""
        pass
    
    @abstractmethod
    async def analyze_error_patterns(self) -> Dict[str, Any]:
        """Analyze error patterns and trends."""
        pass
    
    @abstractmethod
    async def get_accuracy_metrics(self, processing_type: ProcessingType) -> Dict[str, Any]:
        """Get accuracy metrics for specific processing type."""
        pass
    
    @abstractmethod
    async def get_retry_success_rates(self) -> Dict[str, Any]:
        """Get retry success rates for failed operations."""
        pass


class IBusinessAnalytics(ABC):
    """Interface for business analytics operations."""
    
    @abstractmethod
    async def get_cost_analytics(self, time_range: TimeRange) -> Dict[str, Any]:
        """Get cost analytics for operations."""
        pass
    
    @abstractmethod
    async def get_roi_metrics(self) -> Dict[str, Any]:
        """Get return on investment metrics."""
        pass
    
    @abstractmethod
    async def get_growth_metrics(self) -> Dict[str, Any]:
        """Get platform growth metrics."""
        pass
    
    @abstractmethod
    async def get_provider_comparison(self) -> Dict[str, Any]:
        """Compare performance across different providers."""
        pass


class IRealtimeAnalytics(ABC):
    """Interface for real-time analytics operations."""
    
    @abstractmethod
    async def get_current_processing_status(self) -> Dict[str, Any]:
        """Get current processing status in real-time."""
        pass
    
    @abstractmethod
    async def get_live_metrics(self) -> Dict[str, Any]:
        """Get live system metrics."""
        pass
    
    @abstractmethod
    async def get_alert_conditions(self) -> List[Dict[str, Any]]:
        """Get current alert conditions."""
        pass
    
    @abstractmethod
    async def track_processing_event(
        self, 
        media_id: UUID, 
        event_type: str, 
        metadata: Dict[str, Any]
    ) -> None:
        """Track a processing event for real-time analytics."""
        pass


class IAnalyticsExporter(ABC):
    """Interface for analytics export operations."""
    
    @abstractmethod
    async def export_metrics_report(
        self,
        time_range: TimeRange,
        format_type: str = "json"
    ) -> str:
        """Export comprehensive metrics report."""
        pass
    
    @abstractmethod
    async def export_user_report(
        self,
        user_id: UUID,
        format_type: str = "json"
    ) -> str:
        """Export user-specific report."""
        pass
    
    @abstractmethod
    async def export_performance_report(
        self,
        time_range: TimeRange,
        format_type: str = "json"
    ) -> str:
        """Export performance analysis report."""
        pass
    
    @abstractmethod
    async def schedule_recurring_report(
        self,
        report_type: str,
        frequency: str,
        recipients: List[str]
    ) -> str:
        """Schedule recurring analytics reports."""
        pass