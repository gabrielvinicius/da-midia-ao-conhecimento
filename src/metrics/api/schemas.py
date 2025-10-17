"""
Metrics API Schemas - Pydantic models for metrics endpoints
Follows clear data contracts and validation.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


# Request Schemas
class CreateCustomMetricRequest(BaseModel):
    """Request schema for creating custom metrics."""
    name: str = Field(..., description="Metric name")
    metric_type: str = Field(..., description="Type of metric (counter, histogram, gauge)")
    description: str = Field(..., description="Metric description")
    labels: Optional[Dict[str, str]] = Field(None, description="Optional labels")


# Response Schemas
class ProviderMetrics(BaseModel):
    """Provider metrics information."""
    available_metrics: List[str]
    provider_type: str


class BusinessKPIsResponse(BaseModel):
    """Response schema for business KPIs."""
    total_uploads: float
    successful_uploads: float
    upload_success_rate_percent: float
    total_revenue_usd: float
    average_revenue_per_upload: float
    processing_completions: float
    calculated_at: str


class RequestMetrics(BaseModel):
    """Request metrics summary."""
    total_requests: float
    slow_requests: float
    error_requests: float
    slow_request_rate_percent: float
    error_rate_percent: float


class ProcessingMetrics(BaseModel):
    """Processing metrics summary."""
    total_processing: float
    long_processing: float
    long_processing_rate_percent: float


class ResourceMetrics(BaseModel):
    """Resource metrics summary."""
    cpu_usage_percent: float
    memory_usage_percent: float


class PerformanceSummaryResponse(BaseModel):
    """Response schema for performance summary."""
    request_metrics: RequestMetrics
    processing_metrics: ProcessingMetrics
    resource_metrics: ResourceMetrics
    overall_health: str
    calculated_at: str


class MetricsSummaryResponse(BaseModel):
    """Response schema for comprehensive metrics summary."""
    provider_metrics: ProviderMetrics
    business_kpis: Optional[Dict[str, Any]] = None
    performance_summary: Optional[Dict[str, Any]] = None
    generated_at: str


class HealthCheckResponse(BaseModel):
    """Response schema for health check."""
    metrics_provider: str
    business_metrics: str
    performance_metrics: str
    total_metrics: int
    provider_test: Optional[str] = None
    checked_at: str


class TrackingResponse(BaseModel):
    """Response schema for tracking operations."""
    message: str


class ErrorResponse(BaseModel):
    """Response schema for errors."""
    error: str
    detail: Optional[str] = None
    timestamp: str


# Additional specialized schemas
class MetricValue(BaseModel):
    """Individual metric value."""
    name: str
    value: float
    labels: Optional[Dict[str, str]] = None
    timestamp: str


class MetricHistory(BaseModel):
    """Metric history over time."""
    metric_name: str
    values: List[MetricValue]
    time_range: str


class AlertRule(BaseModel):
    """Alert rule configuration."""
    name: str
    condition: str
    threshold: float
    severity: str
    enabled: bool


class AlertStatus(BaseModel):
    """Current alert status."""
    rule_name: str
    current_value: float
    threshold: float
    is_triggered: bool
    last_triggered: Optional[str] = None


class SystemHealth(BaseModel):
    """System health indicators."""
    overall_score: float
    status: str
    components: Dict[str, str]
    issues: List[str]
    recommendations: List[str]


class UsageStatistics(BaseModel):
    """Usage statistics."""
    total_api_calls: int
    unique_users: int
    most_used_endpoints: List[Dict[str, Any]]
    peak_usage_time: str
    average_response_time: float


class PerformanceBreakdown(BaseModel):
    """Detailed performance breakdown."""
    endpoint_performance: Dict[str, Dict[str, float]]
    operation_performance: Dict[str, Dict[str, float]]
    resource_utilization: Dict[str, float]
    bottlenecks: List[str]


class BusinessAnalytics(BaseModel):
    """Business analytics summary."""
    revenue_trends: Dict[str, float]
    user_engagement: Dict[str, Any]
    feature_adoption: Dict[str, float]
    churn_indicators: Dict[str, Any]


class MetricsExportResponse(BaseModel):
    """Response for metrics export."""
    format_type: str
    data: str
    generated_at: str
    row_count: Optional[int] = None


class CustomMetricResponse(BaseModel):
    """Response for custom metric operations."""
    name: str
    metric_type: str
    description: str
    labels: List[str]
    created_at: str
    status: str


class MetricsComparisonResponse(BaseModel):
    """Response for metrics comparison."""
    metric_name: str
    current_period: Dict[str, Any]
    previous_period: Dict[str, Any]
    change_percentage: float
    trend: str
    insights: List[str]