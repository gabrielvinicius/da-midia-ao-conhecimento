# src/metrics/api/routers.py
from fastapi import APIRouter, Depends, Response, HTTPException, status, Query
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from typing import Optional
from uuid import UUID

from src.shared.api.dependencies import get_current_user
from src.auth.domain.user import User
from src.metrics.application.metrics_service import MetricsService
from src.metrics.application.services.business_metrics import BusinessMetrics
from src.metrics.application.services.performance_metrics import PerformanceMetrics
from .dependencies import get_metrics_service, get_business_metrics, get_performance_metrics
from .schemas import (
    MetricsSummaryResponse,
    BusinessKPIsResponse,
    PerformanceSummaryResponse,
    HealthCheckResponse,
    CreateCustomMetricRequest
)

router = APIRouter(
    prefix="/metrics",
    tags=["Metrics"]
)


# Core metrics endpoints
@router.get("/prometheus", summary="Get Prometheus metrics")
async def get_prometheus_metrics():
    """
    Endpoint to expose metrics in Prometheus format.
    """
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/summary", response_model=MetricsSummaryResponse, summary="Get comprehensive metrics summary")
async def get_metrics_summary(
    metrics_service: MetricsService = Depends(get_metrics_service),
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
    metrics_service: MetricsService = Depends(get_metrics_service),
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
    business_metrics: BusinessMetrics = Depends(get_business_metrics),
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
        kpis = business_metrics.get_business_kpis()
        return BusinessKPIsResponse(**kpis)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/business/media-upload", summary="Track media upload event")
async def track_media_upload(
    status: str = Query(..., description="Upload status (success, failed)"),
    media_type: str = Query(..., description="Media type (video, audio, text)"),
    metrics_service: MetricsService = Depends(get_metrics_service),
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
    metrics_service: MetricsService = Depends(get_metrics_service),
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
    metrics_service: MetricsService = Depends(get_metrics_service),
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
    performance_metrics: PerformanceMetrics = Depends(get_performance_metrics),
    current_user: User = Depends(get_current_user),
):
    """Get performance metrics summary."""
    try:
        summary = performance_metrics.get_performance_summary()
        return PerformanceSummaryResponse(**summary)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/performance/api-request", summary="Track API request performance")
async def track_api_request(
    endpoint: str = Query(..., description="API endpoint"),
    method: str = Query(..., description="HTTP method"),
    duration: float = Query(..., description="Request duration in seconds"),
    status_code: int = Query(..., description="HTTP status code"),
    metrics_service: MetricsService = Depends(get_metrics_service),
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
    metrics_service: MetricsService = Depends(get_metrics_service),
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
    metrics_service: MetricsService = Depends(get_metrics_service),
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


# Legacy endpoints for backward compatibility
@router.get("/", summary="Legacy metrics endpoint")
async def get_metrics_legacy():
    """
    Legacy endpoint for Prometheus metrics (backward compatibility).
    Use /metrics/prometheus instead.
    """
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.post("/legacy/upload", summary="Legacy upload tracking")
async def track_upload_legacy(
    status: str = Query(..., description="Upload status"),
    metrics_service: MetricsService = Depends(get_metrics_service),
):
    """Legacy endpoint for tracking uploads."""
    try:
        metrics_service.increment_media_upload(status)
        return {"message": "Upload tracked (legacy)"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))