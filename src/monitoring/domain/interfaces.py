"""Domain interfaces for monitoring module.
Follows Dependency Inversion Principle (DIP).
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID


class MetricType(Enum):
    """Types of metrics that can be collected."""

    COUNTER = "counter"
    HISTOGRAM = "histogram"
    GAUGE = "gauge"
    SUMMARY = "summary"


class TimeRange(Enum):
    """Time ranges for analytics queries."""

    LAST_HOUR = "last_hour"
    LAST_DAY = "last_day"
    LAST_WEEK = "last_week"
    LAST_MONTH = "last_month"
    LAST_YEAR = "last_year"
    ALL_TIME = "all_time"


class ProcessingType(Enum):
    """Types of processing operations."""

    TRANSCRIPTION = "transcription"
    SUMMARIZATION = "summarization"
    MEDIA = "media"


class IMetricsProvider(ABC):
    """Interface for metrics collection providers (Prometheus, DataDog, etc.)."""

    @abstractmethod
    def increment_counter(self, name: str, labels: Optional[Dict[str, str]] = None, value: float = 1.0) -> None:
        pass

    @abstractmethod
    def observe_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        pass

    @abstractmethod
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        pass

    @abstractmethod
    def observe_summary(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        pass

    @abstractmethod
    def get_metric_value(self, name: str, labels: Optional[Dict[str, str]] = None) -> Optional[float]:
        pass

    @abstractmethod
    def list_metrics(self) -> List[str]:
        pass

    @abstractmethod
    def create_dynamic_counter(self, name: str, description: str, labels: List[str]) -> None:
        pass

    @abstractmethod
    def create_dynamic_histogram(self, name: str, description: str, labels: List[str], buckets: Optional[List[float]] = None) -> None:
        pass

    @abstractmethod
    def create_dynamic_gauge(self, name: str, description: str, labels: List[str]) -> None:
        pass


class IAnalyticsRepository(ABC):
    """Interface for analytics data access operations."""

    @abstractmethod
    async def get_average_processing_times(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_processing_times_by_type(self, processing_type: ProcessingType) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_success_failure_rates(self, time_range: TimeRange) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_user_activity_metrics(self, user_id: Optional[UUID] = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_media_type_distribution(self) -> Dict[str, Any]:
        pass


class IAnalyticsQueries(ABC):
    """Interface for analytics query operations."""

    @abstractmethod
    async def estimate_processing_time(self, content_metric: float) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_system_performance_metrics(self, time_range: TimeRange) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_processing_trends(self, days: int = 30) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_user_analytics(self, user_id: UUID) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_media_analytics(self, media_id: UUID) -> Dict[str, Any]:
        pass
