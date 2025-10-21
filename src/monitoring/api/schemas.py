"""
Monitoring API Schemas - Pydantic models for monitoring endpoints
Follows clear data contracts and validation.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from uuid import UUID


# Request Schemas
class ProcessingTimeEstimateRequest(BaseModel):
    """Request schema for processing time estimation."""
    content_metric: float = Field(..., gt=0, description="Content metric (duration, length, etc.)")

class CreateCustomMetricRequest(BaseModel):
    """Request schema for creating custom metrics."""
    name: str = Field(..., description="Metric name")
    metric_type: str = Field(..., description="Type of metric (counter, histogram, gauge)")
    description: str = Field(..., description="Metric description")
    labels: Optional[Dict[str, str]] = Field(None, description="Optional labels")

# Response Schemas
class ProcessingTimeEstimateResponse(BaseModel):
    """Response schema for processing time estimation."""
    estimated_total_seconds: float
    transcription_estimated_seconds: float
    summarization_estimated_seconds: float
    confidence_level: str
    based_on_samples: int


class SuccessRateMetrics(BaseModel):
    """Success rate metrics for a specific operation."""
    completed: int
    failed: int
    total: int
    success_rate: float


class SystemPerformanceResponse(BaseModel):
    """Response schema for system performance metrics."""
    time_range: str
    overall_health_score: float
    success_rates: Dict[str, SuccessRateMetrics]
    user_metrics: Dict[str, Any]
    media_distribution: Dict[str, Any]
    recommendations: List[str]


class TrendMetrics(BaseModel):
    """Trend metrics for a specific period."""
    direction: str
    change_percentage: float


class ProcessingTrendsResponse(BaseModel):
    """Response schema for processing trends."""
    analysis_period_days: int
    current_week: Dict[str, Any]
    monthly_average: Dict[str, Any]
    trend_direction: str
    trend_percentage: float
    insights: List[str]


class UserRanking(BaseModel):
    """User ranking information."""
    tier: str
    percentile: float


class UserAnalyticsResponse(BaseModel):
    """Response schema for user analytics."""
    user_id: str
    metrics: Dict[str, Any]
    ranking: UserRanking
    comparison_to_average: Dict[str, float]
    recommendations: List[str]


class ThroughputMetrics(BaseModel):
    """Throughput metrics."""
    media_per_hour: float
    transcriptions_per_hour: float
    summaries_per_hour: float
    total_operations_per_hour: float


class EfficiencyMetrics(BaseModel):
    """Efficiency metrics."""
    media_success_rate: float
    transcription_success_rate: float
    summarization_success_rate: float


class CapacityUtilization(BaseModel):
    """Capacity utilization metrics."""
    current_utilization_percent: float
    remaining_capacity_percent: float
    operations_to_capacity: int


class ThroughputMetricsResponse(BaseModel):
    """Response schema for throughput metrics."""
    time_range: str
    analysis_period_hours: int
    throughput_metrics: ThroughputMetrics
    efficiency_metrics: EfficiencyMetrics
    capacity_utilization: CapacityUtilization


class Bottleneck(BaseModel):
    """Individual bottleneck information."""
    type: str
    severity: str
    metric: str


class PerformanceSummary(BaseModel):
    """Performance summary metrics."""
    transcription_avg_time: float
    summarization_avg_time: float
    overall_success_rate: float


class BottleneckAnalysisResponse(BaseModel):
    """Response schema for bottleneck analysis."""
    bottleneck_score: int
    severity_level: str
    identified_bottlenecks: List[Bottleneck]
    recommendations: List[str]
    performance_summary: PerformanceSummary


class QualityScore(BaseModel):
    """Quality score metrics."""
    transcription_quality_score: float
    summarization_quality_score: float
    overall_quality_score: float


class ProcessingReliability(BaseModel):
    """Processing reliability metrics."""
    success_rate: float
    average_time: float
    consistency_score: float


class QualityTrend(BaseModel):
    """Quality trend information."""
    direction: str
    change_percentage: float


class QualityMetricsResponse(BaseModel):
    """Response schema for quality metrics."""
    assessment_period: str
    quality_scores: QualityScore
    processing_reliability: Dict[str, ProcessingReliability]
    quality_trend: Dict[str, QualityTrend]
    improvement_areas: List[str]


class ErrorPattern(BaseModel):
    """Error pattern information."""
    pattern_type: str
    severity: str
    description: str


class ErrorFrequency(BaseModel):
    """Error frequency metrics."""
    total_operations: int
    total_errors: int
    overall_error_rate: float
    errors_per_day: float
    error_distribution: Dict[str, int]


class ErrorImpact(BaseModel):
    """Error impact metrics."""
    processing_pipeline_impact: Dict[str, int]
    user_experience_impact: Dict[str, int]


class ErrorTrends(BaseModel):
    """Error trend information."""
    transcription_error_trend: str
    summarization_error_trend: str


class ErrorAnalysisResponse(BaseModel):
    """Response schema for error analysis."""
    analysis_period: str
    error_frequency: ErrorFrequency
    error_impact: ErrorImpact
    error_patterns: List[ErrorPattern]
    error_trends: ErrorTrends
    remediation_suggestions: List[str]


# Additional specialized schemas
class AccuracyMetrics(BaseModel):
    """Accuracy metrics for processing type."""
    success_rate: float
    total_processed: int
    accuracy_score: float
    reliability_index: float


class PerformanceMetrics(BaseModel):
    """Performance metrics for processing type."""
    average_processing_time: float
    min_processing_time: float
    max_processing_time: float
    time_consistency: str


class QualityIndicators(BaseModel):
    """Quality indicators for processing type."""
    speed_quality_ratio: float
    processing_efficiency: float


class QualityBenchmarks(BaseModel):
    """Quality benchmarks for comparison."""
    target_success_rate: float
    target_avg_time: float
    target_consistency: float


class AccuracyMetricsResponse(BaseModel):
    """Response schema for accuracy metrics."""
    processing_type: str
    accuracy_metrics: AccuracyMetrics
    performance_metrics: PerformanceMetrics
    quality_indicators: QualityIndicators
    benchmarks: QualityBenchmarks


class LoadPrediction(BaseModel):
    """Individual load prediction."""
    hour: int
    timestamp: str
    predicted_media_uploads: float
    predicted_processing_load: float
    confidence: str


class LoadSummary(BaseModel):
    """Load prediction summary."""
    peak_load: float
    low_load: float
    average_load: float
    load_variance: float


class LoadPredictionResponse(BaseModel):
    """Response schema for load prediction."""
    prediction_horizon_hours: int
    baseline_metrics: Dict[str, float]
    predictions: List[LoadPrediction]
    summary: LoadSummary
    recommendations: List[str]


class ResourceUtilizationResponse(BaseModel):
    """Response schema for resource utilization."""
    analysis_period: str
    operational_metrics: Dict[str, Any]
    estimated_resource_usage: Dict[str, float]
    efficiency_indicators: Dict[str, float]


class RetryStatistics(BaseModel):
    """Retry statistics for a service."""
    initial_failures: int
    retry_attempts: int
    retry_successes: int
    retry_success_rate: float


class RetryEffectiveness(BaseModel):
    """Retry effectiveness metrics."""
    transcription_retry_success_rate: float
    summarization_retry_success_rate: float
    overall_retry_effectiveness: float


class RetryAnalysisResponse(BaseModel):
    """Response schema for retry analysis."""
    analysis_period: str
    retry_statistics: Dict[str, RetryStatistics]
    retry_effectiveness: RetryEffectiveness
    retry_recommendations: List[str]

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
