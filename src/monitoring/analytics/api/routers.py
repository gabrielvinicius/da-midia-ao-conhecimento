"""
Analytics API Router - Exposes analytics endpoints
Follows SOLID principles with dependency injection.
"""
from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import Optional
from uuid import UUID

from src.shared.api.dependencies import get_current_user
from src.auth.domain.user import User
from src.analytics.domain.interfaces import TimeRange, ProcessingType
from .dependencies import (
    get_analytics_queries, 
    get_performance_analytics, 
    get_quality_analytics
)
from .schemas import (
    ProcessingTimeEstimateRequest,
    ProcessingTimeEstimateResponse,
    SystemPerformanceResponse,
    ProcessingTrendsResponse,
    UserAnalyticsResponse,
    ThroughputMetricsResponse,
    BottleneckAnalysisResponse,
    QualityMetricsResponse,
    ErrorAnalysisResponse
)

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
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


# Performance Analytics Endpoints
@router.get("/performance/throughput", response_model=ThroughputMetricsResponse)
async def get_throughput_metrics(
    time_range: TimeRange = Query(TimeRange.LAST_DAY, description="Time range for throughput analysis"),
    performance_analytics = Depends(get_performance_analytics),
):
    """Get system throughput metrics."""
    try:
        result = await performance_analytics.calculate_throughput_metrics(time_range)
        return ThroughputMetricsResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/performance/bottlenecks", response_model=BottleneckAnalysisResponse)
async def analyze_bottlenecks(
    performance_analytics = Depends(get_performance_analytics),
):
    """Identify system bottlenecks."""
    try:
        result = await performance_analytics.analyze_bottlenecks()
        return BottleneckAnalysisResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/performance/resource-utilization")
async def get_resource_utilization(
    performance_analytics = Depends(get_performance_analytics),
):
    """Get resource utilization metrics."""
    try:
        result = await performance_analytics.get_resource_utilization()
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/performance/load-prediction")
async def predict_processing_load(
    hours_ahead: int = Query(24, ge=1, le=168, description="Hours to predict ahead"),
    performance_analytics = Depends(get_performance_analytics),
):
    """Predict processing load for the next N hours."""
    try:
        result = await performance_analytics.predict_processing_load(hours_ahead)
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Quality Analytics Endpoints
@router.get("/quality/metrics", response_model=QualityMetricsResponse)
async def get_quality_metrics(
    quality_analytics = Depends(get_quality_analytics),
):
    """Get processing quality metrics."""
    try:
        result = await quality_analytics.get_processing_quality_metrics()
        return QualityMetricsResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/quality/errors", response_model=ErrorAnalysisResponse)
async def analyze_error_patterns(
    quality_analytics = Depends(get_quality_analytics),
):
    """Analyze error patterns and trends."""
    try:
        result = await quality_analytics.analyze_error_patterns()
        return ErrorAnalysisResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/quality/accuracy/{processing_type}")
async def get_accuracy_metrics(
    processing_type: ProcessingType,
    quality_analytics = Depends(get_quality_analytics),
):
    """Get accuracy metrics for specific processing type."""
    try:
        result = await quality_analytics.get_accuracy_metrics(processing_type)
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/quality/retry-rates")
async def get_retry_success_rates(
    quality_analytics = Depends(get_quality_analytics),
):
    """Get retry success rates for failed operations."""
    try:
        result = await quality_analytics.get_retry_success_rates()
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Admin-only endpoints
@router.get("/admin/comprehensive-report")
async def get_comprehensive_analytics_report(
    time_range: TimeRange = Query(TimeRange.LAST_WEEK, description="Time range for report"),
    current_user: User = Depends(get_current_user),
    analytics_queries = Depends(get_analytics_queries),
    performance_analytics = Depends(get_performance_analytics),
    quality_analytics = Depends(get_quality_analytics),
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
        throughput_metrics = await performance_analytics.calculate_throughput_metrics(time_range)
        bottleneck_analysis = await performance_analytics.analyze_bottlenecks()
        quality_metrics = await quality_analytics.get_processing_quality_metrics()
        error_analysis = await quality_analytics.analyze_error_patterns()
        
        return {
            "report_type": "comprehensive_analytics",
            "time_range": time_range.value,
            "generated_at": "2024-01-01T00:00:00Z",  # Would use actual timestamp
            "system_performance": system_performance,
            "throughput_metrics": throughput_metrics,
            "bottleneck_analysis": bottleneck_analysis,
            "quality_metrics": quality_metrics,
            "error_analysis": error_analysis
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))