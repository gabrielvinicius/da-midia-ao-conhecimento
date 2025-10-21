"""
Monitoring API Router - Exposes monitoring endpoints
Follows SOLID principles with dependency injection.
"""
from fastapi import APIRouter, Depends, Query, HTTPException, status, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from typing import Optional
from uuid import UUID

from src.shared.api.dependencies import get_current_user
from src.auth.domain.user import User
from src.monitoring.domain.interfaces import TimeRange, ProcessingType
from .dependencies import (
    get_analytics_queries, 
    get_metrics_service
)
from .schemas import (
    ProcessingTimeEstimateRequest,
    ProcessingTimeEstimateResponse,
    SystemPerformanceResponse,
    ProcessingTrendsResponse,
    UserAnalyticsResponse,
    MetricsSummaryResponse,
    BusinessKPIsResponse,
    PerformanceSummaryResponse,
    HealthCheckResponse,
    CreateCustomMetricRequest
)

router = APIRouter(
    prefix="/monitoring",
    tags=["Monitoring"],
    dependencies=[Depends(get_current_user)]
)


# Core Analytics Endpoints
@router.post("/estimate-processing-time", response_model=ProcessingTimeEstimateResponse)
async def estimate_processing_time(
    request: ProcessingTimeEstimateRequest,
    analytics_queries = Depends(get_analytics_queries),
):
    """Estimate processing time based on content metric and historical data."""
    try:
        result = await analytics_queries.estimate_processing_time(request.content_metric)
        return ProcessingTimeEstimateResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/system-performance", response_model=SystemPerformanceResponse)
async def get_system_performance(
    time_range: TimeRange = Query(TimeRange.LAST_WEEK, description="Time range for analysis"),
    analytics_queries = Depends(get_analytics_queries),
):
    """Get comprehensive system performance metrics."""
    try:
        result = await analytics_queries.get_system_performance_metrics(time_range)
        return SystemPerformanceResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/processing-trends", response_model=ProcessingTrendsResponse)
async def get_processing_trends(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    analytics_queries = Depends(get_analytics_queries),
):
    """Get processing trends over time."""
    try:
        result = await analytics_queries.get_processing_trends(days)
        return ProcessingTrendsResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/user/{user_id}", response_model=UserAnalyticsResponse)
async def get_user_analytics(
    user_id: UUID,
    analytics_queries = Depends(get_analytics_queries),
    current_user: User = Depends(get_current_user),
):
    """Get analytics for specific user."""
    # Users can only view their own analytics unless they're admin
    if str(user_id) != str(current_user.id) and (not current_user.role or current_user.role.value != "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own analytics"
        )
    
    try:
        result = await analytics_queries.get_user_analytics(user_id)
        return UserAnalyticsResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/media/{media_id}")
async def get_media_analytics(
    media_id: UUID,
    analytics_queries = Depends(get_analytics_queries),
    current_user: User = Depends(get_current_user),
):
    """Get analytics for specific media item."""
    try:
        result = await analytics_queries.get_media_analytics(media_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Admin-only endpoints
@router.get("/admin/comprehensive-report")
async def get_comprehensive_analytics_report(
    time_range: TimeRange = Query(TimeRange.LAST_WEEK, description="Time range for report"),
    current_user: User = Depends(get_current_user),
    analytics_queries = Depends(get_analytics_queries),
    metrics_service = Depends(get_metrics_service),
):
    """Get comprehensive analytics report (admin only)."""
    if not current_user.role or current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        # Gather comprehensive analytics data
        system_performance = await analytics_queries.get_system_performance_metrics(time_range)
        metrics_summary = metrics_service.get_metrics_summary()
        health_check = metrics_service.health_check()
        
        return {
            "report_type": "comprehensive_analytics",
            "time_range": time_range.value,
            "generated_at": "2024-01-01T00:00:00Z",  # Would use actual timestamp
            "system_performance": system_performance,
            "metrics_summary": metrics_summary,
            "health_check": health_check
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

# Core metrics endpoints
@router.get("/prometheus", summary="Get Prometheus metrics")
async def get_prometheus_metrics():
    """
    Endpoint to expose metrics in Prometheus format.
    """
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/summary", response_model=MetricsSummaryResponse, summary="Get comprehensive metrics summary")
async def get_metrics_summary(
    metrics_service = Depends(get_metrics_service),
    current_user: User = Depends(get_current_user),
):
    """Get comprehensive metrics summary from all services."""
    try:
        summary = metrics_service.get_metrics_summary()
        return MetricsSummaryResponse(**summary)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/health", response_model=HealthCheckResponse, summary="Metrics system health check")
async def get_metrics_health(
    metrics_service = Depends(get_metrics_service),
):
    """Perform health check of the metrics system."""
    try:
        health = metrics_service.health_check()
        return HealthCheckResponse(**health)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Business metrics endpoints
@router.get("/business/kpis", response_model=BusinessKPIsResponse, summary="Get business KPIs")
async def get_business_kpis(
    metrics_service = Depends(get_metrics_service),
    current_user: User = Depends(get_current_user),
):
    """Get key business performance indicators."""
    # Only admins can view business metrics
    if not current_user.role or current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required to view business metrics"
        )
    
    try:
        # Assuming MetricsService has a method to get business KPIs
        kpis = metrics_service.get_business_kpis() # This method needs to be implemented in MetricsService
        return BusinessKPIsResponse(**kpis)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/business/media-upload", summary="Track media upload event")
async def track_media_upload(
    status: str = Query(..., description="Upload status (success, failed)"),
    media_type: str = Query(..., description="Media type (video, audio, text)"),
    metrics_service = Depends(get_metrics_service),
    current_user: User = Depends(get_current_user),
):
    """Track a media upload event with business context."""
    try:
        metrics_service.track_media_upload_with_context(status, media_type, current_user.id)
        return {"message": "Media upload tracked successfully"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/business/user-activity", summary="Track user activity")
async def track_user_activity(
    action: str = Query(..., description="Action performed"),
    resource_type: str = Query(..., description="Resource type"),
    metrics_service = Depends(get_metrics_service),
    current_user: User = Depends(get_current_user),
):
    """Track user activity for engagement analytics."""
    try:
        metrics_service.track_user_activity(current_user.id, action, resource_type)
        return {"message": "User activity tracked successfully"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/business/processing-completion", summary="Track processing completion")
async def track_processing_completion(
    operation: str = Query(..., description="Operation type"),
    status: str = Query(..., description="Completion status"),
    duration: float = Query(..., description="Processing duration in seconds"),
    metrics_service = Depends(get_metrics_service),
    current_user: User = Depends(get_current_user),
):
    """Track processing completion event."""
    try:
        metrics_service.track_processing_completion(operation, status, duration)
        return {"message": "Processing completion tracked successfully"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Performance metrics endpoints
@router.get("/performance/summary", response_model=PerformanceSummaryResponse, summary="Get performance summary")
async def get_performance_summary(
    metrics_service = Depends(get_metrics_service),
    current_user: User = Depends(get_current_user),
):
    """Get performance metrics summary."""
    try:
        # Assuming MetricsService has a method to get performance summary
        summary = metrics_service.get_performance_summary() # This method needs to be implemented in MetricsService
        return PerformanceSummaryResponse(**summary)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/performance/api-request", summary="Track API request performance")
async def track_api_request(
    endpoint: str = Query(..., description="API endpoint"),
    method: str = Query(..., description="HTTP method"),
    duration: float = Query(..., description="Request duration in seconds"),
    status_code: int = Query(..., description="HTTP status code"),
    metrics_service = Depends(get_metrics_service),
):
    """Track API request performance metrics."""
    try:
        metrics_service.track_api_request(endpoint, method, duration, status_code)
        return {"message": "API request performance tracked successfully"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/performance/system-resource", summary="Track system resource usage")
async def track_system_resource(
    resource: str = Query(..., description="Resource type (cpu, memory, disk)"),
    usage: float = Query(..., description="Usage value"),
    unit: str = Query(..., description="Unit of measurement"),
    metrics_service = Depends(get_metrics_service),
    current_user: User = Depends(get_current_user),
):
    """Track system resource usage."""
    # Only admins can track system resources
    if not current_user.role or current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required to track system resources"
        )
    
    try:
        metrics_service.track_system_resource(resource, usage, unit)
        return {"message": "System resource usage tracked successfully"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Custom metrics endpoints
@router.post("/custom", summary="Create custom metric")
async def create_custom_metric(
    request: CreateCustomMetricRequest,
    metrics_service = Depends(get_metrics_service),
    current_user: User = Depends(get_current_user),
):
    """Create a custom metric (admin only)."""
    if not current_user.role or current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required to create custom metrics"
        )
    
    try:
        metrics_service.create_custom_metric(
            request.name,
            request.metric_type,
            request.description,
            request.labels
        )
        return {"message": f"Custom metric '{request.name}' created successfully"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))