"""
Providers API Schemas - Pydantic models for provider endpoints
Follows clear data contracts and validation.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from uuid import UUID

from src.providers.domain.interfaces import ProviderType, ProviderCapability


# Request Schemas
class ProviderSelectionRequest(BaseModel):
    """Request schema for provider selection."""
    provider_type: ProviderType = Field(..., description="Type of provider required")
    required_capabilities: Optional[List[str]] = Field(None, description="Required provider capabilities")
    preferences: Optional[Dict[str, Any]] = Field(None, description="Selection preferences")


class ProviderRegistrationRequest(BaseModel):
    """Request schema for provider registration."""
    name: str = Field(..., description="Provider name")
    provider_type: ProviderType = Field(..., description="Provider type")
    version: str = Field("1.0.0", description="Provider version")
    capabilities: List[str] = Field(default_factory=list, description="Provider capabilities")
    configuration: Dict[str, Any] = Field(default_factory=dict, description="Provider configuration")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Provider metadata")


class ProviderConfigurationUpdateRequest(BaseModel):
    """Request schema for updating provider configuration."""
    configuration: Dict[str, Any] = Field(..., description="New configuration")
    validate_only: bool = Field(False, description="Only validate, don't apply")


# Response Schemas
class ProviderInfo(BaseModel):
    """Basic provider information."""
    name: str
    type: str
    version: str
    capabilities: List[str]
    status: Optional[str] = None


class ProviderSummaryResponse(BaseModel):
    """Response schema for provider summary."""
    total_providers: int
    providers_by_type: Dict[str, int]
    active_providers: int
    capabilities_coverage: Dict[str, int]
    initialized: bool
    legacy_providers: Optional[Dict[str, List[str]]] = None


class ProvidersListResponse(BaseModel):
    """Response schema for provider listing."""
    providers: List[ProviderInfo]
    total_count: int
    filter_applied: Dict[str, Any]


class ProviderDetailResponse(BaseModel):
    """Response schema for detailed provider information."""
    name: str
    type: str
    version: str
    capabilities: List[str]
    configuration: Dict[str, Any]
    health_status: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class ProviderSelectionResponse(BaseModel):
    """Response schema for provider selection."""
    selected_provider: Optional[ProviderInfo]
    selection_reason: str
    alternatives: List[ProviderInfo]


class ProviderHealthStatus(BaseModel):
    """Provider health status information."""
    provider_name: str
    provider_type: str
    status: str
    last_check: str
    response_time_ms: float
    error_message: Optional[str] = None
    is_healthy: bool


class ProviderHealthResponse(BaseModel):
    """Response schema for provider health check."""
    health_results: Dict[str, Dict[str, Any]]
    timestamp: str
    overall_status: str


class SystemHealthResponse(BaseModel):
    """Response schema for system health summary."""
    overall_status: str
    total_providers: int
    healthy_providers: int
    unhealthy_providers: int
    provider_health_summary: Dict[str, Dict[str, Any]]
    issues: List[str]
    recommendations: List[str]


class ProviderMetricsResponse(BaseModel):
    """Response schema for provider metrics."""
    provider_name: str
    provider_type: str
    performance_metrics: Dict[str, Any]
    reliability_metrics: Dict[str, Any]
    cost_metrics: Dict[str, Any]
    last_updated: str


# Performance and Analytics Schemas
class PerformanceMetrics(BaseModel):
    """Performance metrics for a provider."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate_percentage: float
    average_response_time_ms: float
    total_processing_time_ms: float


class ReliabilityMetrics(BaseModel):
    """Reliability metrics for a provider."""
    uptime_percentage: float
    error_rate_percentage: float
    last_failure: Optional[str] = None
    consecutive_failures: int
    mean_time_between_failures: Optional[float] = None


class CostMetrics(BaseModel):
    """Cost metrics for a provider."""
    total_cost: float
    cost_per_request: float
    cost_trend: str  # increasing, decreasing, stable
    estimated_monthly_cost: float


class LoadMetrics(BaseModel):
    """Load metrics for a provider."""
    current_load: float
    max_capacity: float
    load_percentage: float
    throughput_per_minute: float


class ComprehensiveProviderMetrics(BaseModel):
    """Comprehensive metrics for a provider."""
    provider_name: str
    provider_type: str
    performance: PerformanceMetrics
    reliability: ReliabilityMetrics
    cost: CostMetrics
    load: LoadMetrics
    period_start: str
    period_end: str


# Analytics and Comparison Schemas
class ProviderComparison(BaseModel):
    """Comparison between multiple providers."""
    provider_type: str
    comparison_metrics: List[str]
    time_range: str
    providers: Dict[str, Dict[str, Any]]
    best_performer: Dict[str, str]  # metric -> provider_name
    recommendations: List[str]


class ProviderAnalyticsResponse(BaseModel):
    """Response schema for provider analytics."""
    provider_name: str
    provider_type: str
    analysis_period: str
    performance_trends: Dict[str, Any]
    reliability_analysis: Dict[str, Any]
    cost_analysis: Dict[str, Any]
    optimization_recommendations: List[str]
    predicted_metrics: Dict[str, Any]


# Configuration and Management Schemas
class ProviderConfigurationResponse(BaseModel):
    """Response schema for provider configuration."""
    provider_name: str
    provider_type: str
    configuration: Dict[str, Any]
    validation_status: str
    validation_errors: List[str]
    last_updated: str


class ProviderCapabilitiesResponse(BaseModel):
    """Response schema for provider capabilities."""
    provider_name: str
    provider_type: str
    supported_capabilities: List[str]
    capability_details: Dict[str, Dict[str, Any]]
    compatibility_matrix: Dict[str, bool]


# Failover and Load Balancing Schemas
class FailoverEvent(BaseModel):
    """Failover event information."""
    id: str
    primary_provider: str
    fallback_provider: str
    provider_type: str
    failure_reason: str
    recovery_action: str
    occurred_at: str
    resolved_at: Optional[str] = None
    is_resolved: bool


class FailoverHistoryResponse(BaseModel):
    """Response schema for failover history."""
    provider_name: Optional[str] = None
    provider_type: Optional[str] = None
    failover_events: List[FailoverEvent]
    total_events: int
    time_range: str
    statistics: Dict[str, Any]


class LoadBalancingStatus(BaseModel):
    """Load balancing status for providers."""
    provider_type: str
    active_providers: List[str]
    load_distribution: Dict[str, float]
    balancing_strategy: str
    last_rebalance: str
    next_rebalance: str


# Discovery and Registration Schemas
class DiscoveredProvider(BaseModel):
    """Information about a discovered provider."""
    name: str
    type: str
    version: str
    location: str
    capabilities: List[str]
    health_status: str
    auto_registerable: bool


class ProviderDiscoveryResponse(BaseModel):
    """Response schema for provider discovery."""
    provider_type: str
    discovered_providers: List[DiscoveredProvider]
    total_discovered: int
    auto_registered: int
    discovery_timestamp: str


class ProviderRegistrationResponse(BaseModel):
    """Response schema for provider registration."""
    provider_name: str
    provider_type: str
    registration_status: str
    registration_timestamp: str
    initialization_status: str
    health_check_status: str
    assigned_id: Optional[str] = None


# Cost Management Schemas
class CostBreakdown(BaseModel):
    """Cost breakdown by provider."""
    time_range: str
    total_cost: float
    cost_by_provider: Dict[str, float]
    cost_by_type: Dict[str, float]
    cost_trends: Dict[str, str]
    cost_optimization_potential: float


class CostAlert(BaseModel):
    """Cost alert information."""
    alert_id: str
    provider_name: str
    provider_type: str
    threshold: float
    current_cost: float
    alert_type: str  # threshold_exceeded, trend_warning, etc.
    created_at: str
    acknowledged: bool


class CostOptimizationResponse(BaseModel):
    """Response schema for cost optimization."""
    provider_type: str
    current_costs: Dict[str, float]
    optimization_recommendations: List[Dict[str, Any]]
    potential_savings: float
    implementation_complexity: str
    estimated_roi: Dict[str, Any]


# Advanced Analytics Schemas
class ProviderBenchmark(BaseModel):
    """Benchmark data for providers."""
    provider_name: str
    provider_type: str
    benchmark_metrics: Dict[str, float]
    industry_percentile: float
    comparison_with_peers: Dict[str, Any]
    improvement_areas: List[str]


class CapacityPrediction(BaseModel):
    """Capacity prediction for a provider."""
    provider_name: str
    provider_type: str
    prediction_horizon_hours: int
    predicted_load: List[Dict[str, Any]]
    capacity_warnings: List[str]
    scaling_recommendations: List[str]


class SystemOptimizationResponse(BaseModel):
    """Response schema for system optimization."""
    analysis_timestamp: str
    overall_efficiency_score: float
    provider_recommendations: Dict[str, List[str]]
    load_balancing_suggestions: List[str]
    cost_optimization_opportunities: List[str]
    reliability_improvements: List[str]
    performance_enhancements: List[str]