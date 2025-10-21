"""
Domain interfaces for metrics module.
Follows Dependency Inversion Principle (DIP).
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from uuid import UUID
from enum import Enum
from datetime import datetime


class MetricType(Enum):
    """Types of metrics that can be collected."""
    COUNTER = "counter"
    HISTOGRAM = "histogram"
    GAUGE = "gauge"
    SUMMARY = "summary"


class MetricCategory(Enum):
    """Categories of metrics for organization."""
    BUSINESS = "business"
    PERFORMANCE = "performance"
    SYSTEM = "system"
    USER = "user"
    SECURITY = "security"
    ERROR = "error"


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IMetricsProvider(ABC):
    """Interface for metrics collection providers (Prometheus, DataDog, etc.)."""
    
    @abstractmethod
    def increment_counter(self, name: str, labels: Optional[Dict[str, str]] = None, value: float = 1.0) -> None:
        """Increment a counter metric."""
        pass
    
    @abstractmethod
    def observe_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Observe a value in a histogram metric."""
        pass
    
    @abstractmethod
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge metric value."""
        pass
    
    @abstractmethod
    def observe_summary(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Observe a value in a summary metric."""
        pass
    
    @abstractmethod
    def get_metric_value(self, name: str, labels: Optional[Dict[str, str]] = None) -> Optional[float]:
        """Get current value of a metric."""
        pass
    
    @abstractmethod
    def list_metrics(self) -> List[str]:
        """List all available metrics."""
        pass


class IMetricsCollector(ABC):
    """Interface for collecting domain-specific metrics."""
    
    @abstractmethod
    def collect_business_metrics(self) -> Dict[str, Any]:
        """Collect business-related metrics."""
        pass
    
    @abstractmethod
    def collect_performance_metrics(self) -> Dict[str, Any]:
        """Collect performance-related metrics."""
        pass
    
    @abstractmethod
    def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system-related metrics."""
        pass
    
    @abstractmethod
    def collect_user_metrics(self) -> Dict[str, Any]:
        """Collect user-related metrics."""
        pass


class IBusinessMetrics(ABC):
    """Interface for business metrics operations."""
    
    @abstractmethod
    def track_media_upload(self, status: str, media_type: str, user_id: UUID) -> None:
        """Track media upload events."""
        pass
    
    @abstractmethod
    def track_processing_completion(self, operation: str, status: str, duration: float) -> None:
        """Track processing completion events."""
        pass
    
    @abstractmethod
    def track_user_activity(self, user_id: UUID, action: str, resource_type: str) -> None:
        """Track user activity events."""
        pass
    
    @abstractmethod
    def track_revenue_event(self, amount: float, currency: str, user_id: UUID) -> None:
        """Track revenue-related events."""
        pass
    
    @abstractmethod
    def get_business_kpis(self) -> Dict[str, Any]:
        """Get key business performance indicators."""
        pass


class IPerformanceMetrics(ABC):
    """Interface for performance metrics operations."""
    
    @abstractmethod
    def track_request_duration(self, endpoint: str, method: str, duration: float, status_code: int) -> None:
        """Track HTTP request duration."""
        pass
    
    @abstractmethod
    def track_processing_duration(self, operation: str, duration: float, provider: str) -> None:
        """Track processing operation duration."""
        pass
    
    @abstractmethod
    def track_queue_size(self, queue_name: str, size: int) -> None:
        """Track queue sizes."""
        pass
    
    @abstractmethod
    def track_resource_usage(self, resource: str, usage: float, unit: str) -> None:
        """Track resource usage (CPU, memory, etc.)."""
        pass
    
    @abstractmethod
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance metrics summary."""
        pass


class IErrorMetrics(ABC):
    """Interface for error tracking metrics."""
    
    @abstractmethod
    def track_error(self, error_type: str, service: str, severity: str, details: Optional[str] = None) -> None:
        """Track error occurrences."""
        pass
    
    @abstractmethod
    def track_exception(self, exception_type: str, service: str, stack_trace: Optional[str] = None) -> None:
        """Track exceptions."""
        pass
    
    @abstractmethod
    def track_validation_error(self, field: str, error_type: str, service: str) -> None:
        """Track validation errors."""
        pass
    
    @abstractmethod
    def get_error_rates(self) -> Dict[str, Any]:
        """Get error rates and statistics."""
        pass
    
    @abstractmethod
    def get_top_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most frequent errors."""
        pass


class ISecurityMetrics(ABC):
    """Interface for security metrics operations."""
    
    @abstractmethod
    def track_authentication_attempt(self, success: bool, user_id: Optional[UUID] = None, ip_address: Optional[str] = None) -> None:
        """Track authentication attempts."""
        pass
    
    @abstractmethod
    def track_authorization_failure(self, user_id: UUID, resource: str, action: str) -> None:
        """Track authorization failures."""
        pass
    
    @abstractmethod
    def track_suspicious_activity(self, activity_type: str, user_id: Optional[UUID] = None, details: Optional[str] = None) -> None:
        """Track suspicious activities."""
        pass
    
    @abstractmethod
    def get_security_summary(self) -> Dict[str, Any]:
        """Get security metrics summary."""
        pass


class IMetricsAggregator(ABC):
    """Interface for metrics aggregation and analysis."""
    
    @abstractmethod
    def aggregate_by_time(self, metric_name: str, time_window: str, labels: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """Aggregate metrics by time windows."""
        pass
    
    @abstractmethod
    def calculate_percentiles(self, metric_name: str, percentiles: List[float], labels: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """Calculate percentiles for a metric."""
        pass
    
    @abstractmethod
    def compare_periods(self, metric_name: str, current_period: str, previous_period: str) -> Dict[str, Any]:
        """Compare metrics between periods."""
        pass
    
    @abstractmethod
    def detect_anomalies(self, metric_name: str, threshold: float) -> List[Dict[str, Any]]:
        """Detect anomalies in metrics."""
        pass


class IMetricsAlerts(ABC):
    """Interface for metrics-based alerting."""
    
    @abstractmethod
    def create_alert_rule(self, name: str, condition: str, threshold: float, severity: AlertSeverity) -> str:
        """Create an alert rule."""
        pass
    
    @abstractmethod
    def evaluate_alerts(self) -> List[Dict[str, Any]]:
        """Evaluate all alert rules."""
        pass
    
    @abstractmethod
    def trigger_alert(self, rule_name: str, current_value: float, details: Optional[str] = None) -> None:
        """Trigger an alert."""
        pass
    
    @abstractmethod
    def acknowledge_alert(self, alert_id: str, user_id: UUID) -> None:
        """Acknowledge an alert."""
        pass
    
    @abstractmethod
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get currently active alerts."""
        pass


class IMetricsExporter(ABC):
    """Interface for metrics export operations."""
    
    @abstractmethod
    def export_prometheus_format(self) -> str:
        """Export metrics in Prometheus format."""
        pass
    
    @abstractmethod
    def export_json_format(self, metrics_filter: Optional[List[str]] = None) -> Dict[str, Any]:
        """Export metrics in JSON format."""
        pass
    
    @abstractmethod
    def export_csv_format(self, metric_name: str, time_range: str) -> str:
        """Export metric data in CSV format."""
        pass
    
    @abstractmethod
    def schedule_export(self, format_type: str, frequency: str, destination: str) -> str:
        """Schedule periodic metric exports."""
        pass


class IMetricsRepository(ABC):
    """Interface for metrics persistence operations."""
    
    @abstractmethod
    async def store_metric_sample(self, name: str, value: float, labels: Dict[str, str], timestamp: datetime) -> None:
        """Store a metric sample."""
        pass
    
    @abstractmethod
    async def query_metrics(self, query: str, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Query stored metrics."""
        pass
    
    @abstractmethod
    async def get_metric_metadata(self, metric_name: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a metric."""
        pass
    
    @abstractmethod
    async def cleanup_old_metrics(self, retention_days: int) -> int:
        """Clean up old metric data."""
        pass


class ICustomMetrics(ABC):
    """Interface for custom application-specific metrics."""
    
    @abstractmethod
    def define_custom_metric(self, name: str, metric_type: MetricType, description: str, labels: List[str]) -> None:
        """Define a custom metric."""
        pass
    
    @abstractmethod
    def track_custom_event(self, metric_name: str, value: float, labels: Dict[str, str]) -> None:
        """Track a custom event."""
        pass
    
    @abstractmethod
    def get_custom_metrics(self) -> List[Dict[str, Any]]:
        """Get all custom metrics."""
        pass
    
    @abstractmethod
    def delete_custom_metric(self, metric_name: str) -> bool:
        """Delete a custom metric."""
        pass