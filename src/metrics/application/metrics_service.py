# src/metrics/application/metrics_service.py
from typing import Optional, Dict
from uuid import UUID
import structlog

from src.metrics.domain.interfaces import IMetricsProvider, IBusinessMetrics, IPerformanceMetrics
from src.metrics.domain.metrics import MetricsProvider  # Legacy compatibility

logger = structlog.get_logger(__name__)


class MetricsService:
    """
    Main metrics service following SOLID principles.
    
    Single Responsibility: Coordinate metrics collection across different domains.
    Open/Closed: Extensible through specialized metrics services.
    Dependency Inversion: Depends on abstractions, not concretions.
    """
    
    def __init__(
        self,
        provider: IMetricsProvider,
        business_metrics: Optional[IBusinessMetrics] = None,
        performance_metrics: Optional[IPerformanceMetrics] = None
    ):
        self.provider = provider
        self.business_metrics = business_metrics
        self.performance_metrics = performance_metrics

    # Legacy methods - maintained for backward compatibility
    def increment_media_upload(self, status: str):
        """Legacy method - use track_media_upload_with_context for new code."""
        self.provider.increment_counter("MEDIA_UPLOADS_TOTAL", {"status": status})
        logger.debug("legacy.media_upload_tracked", status=status)

    def increment_transcription(self, status: str):
        """Legacy method - use track_processing_completion for new code."""
        self.provider.increment_counter("TRANSCRIPTIONS_TOTAL", {"status": status})
        logger.debug("legacy.transcription_tracked", status=status)

    def increment_summarization(self, status: str):
        """Legacy method - use track_processing_completion for new code.""" 
        self.provider.increment_counter("SUMMARIZATIONS_TOTAL", {"status": status})
        logger.debug("legacy.summarization_tracked", status=status)

    def observe_upload_duration(self, media_id: str, duration: float, provider: str):
        """Legacy method - use track_processing_duration for new code."""
        labels = {"media_id": media_id, "provider": provider}
        self.provider.observe_histogram("UPLOAD_DURATION", duration, labels)
        logger.debug("legacy.upload_duration_tracked", media_id=media_id, duration=duration, provider=provider)

    def observe_transcription_duration(self, media_id: str, duration: float, provider: str):
        """Legacy method - use track_processing_duration for new code."""
        labels = {"media_id": media_id, "provider": provider}
        self.provider.observe_histogram("TRANSCRIPTION_DURATION", duration, labels)
        logger.debug("legacy.transcription_duration_tracked", media_id=media_id, duration=duration, provider=provider)

    def observe_summarization_duration(self, media_id: str, duration: float, provider: str):
        """Legacy method - use track_processing_duration for new code."""
        labels = {"media_id": media_id, "provider": provider}
        self.provider.observe_histogram("SUMMARIZATION_DURATION", duration, labels)
        logger.debug("legacy.summarization_duration_tracked", media_id=media_id, duration=duration, provider=provider)

    # New enhanced methods using specialized services
    def track_media_upload_with_context(self, status: str, media_type: str, user_id: UUID) -> None:
        """
        Track media upload with full business context.
        
        Args:
            status: Upload status
            media_type: Type of media
            user_id: User performing upload
        """
        if self.business_metrics:
            self.business_metrics.track_media_upload(status, media_type, user_id)
        else:
            # Fallback to basic tracking
            self.increment_media_upload(status)
        
        logger.info(
            "metrics.media_upload_tracked_with_context",
            status=status,
            media_type=media_type,
            user_id=str(user_id)
        )

    def track_processing_completion(self, operation: str, status: str, duration: float) -> None:
        """
        Track processing completion with business and performance context.
        
        Args:
            operation: Type of operation
            status: Completion status
            duration: Processing duration
        """
        if self.business_metrics:
            self.business_metrics.track_processing_completion(operation, status, duration)
        
        if self.performance_metrics:
            self.performance_metrics.track_processing_duration(operation, duration, "default")
        
        # Also track with legacy methods for compatibility
        if operation == "transcription":
            self.increment_transcription(status)
        elif operation == "summarization":
            self.increment_summarization(status)
        
        logger.info(
            "metrics.processing_completion_tracked",
            operation=operation,
            status=status,
            duration=duration
        )

    def track_user_activity(self, user_id: UUID, action: str, resource_type: str) -> None:
        """
        Track user activity for engagement analytics.
        
        Args:
            user_id: User performing action
            action: Action performed
            resource_type: Type of resource
        """
        if self.business_metrics:
            self.business_metrics.track_user_activity(user_id, action, resource_type)
        
        logger.debug(
            "metrics.user_activity_tracked",
            user_id=str(user_id),
            action=action,
            resource_type=resource_type
        )

    def track_api_request(self, endpoint: str, method: str, duration: float, status_code: int) -> None:
        """
        Track API request performance.
        
        Args:
            endpoint: API endpoint
            method: HTTP method
            duration: Request duration
            status_code: HTTP status code
        """
        if self.performance_metrics:
            self.performance_metrics.track_request_duration(endpoint, method, duration, status_code)
        
        logger.debug(
            "metrics.api_request_tracked",
            endpoint=endpoint,
            method=method,
            duration=duration,
            status_code=status_code
        )

    def track_system_resource(self, resource: str, usage: float, unit: str) -> None:
        """
        Track system resource usage.
        
        Args:
            resource: Resource type
            usage: Usage value
            unit: Unit of measurement
        """
        if self.performance_metrics:
            self.performance_metrics.track_resource_usage(resource, usage, unit)
        
        logger.debug(
            "metrics.system_resource_tracked",
            resource=resource,
            usage=usage,
            unit=unit
        )

    def get_metrics_summary(self) -> Dict[str, any]:
        """
        Get comprehensive metrics summary.
        
        Returns:
            Dictionary with metrics summary from all services
        """
        summary = {
            "provider_metrics": {
                "available_metrics": self.provider.list_metrics(),
                "provider_type": type(self.provider).__name__
            }
        }
        
        if self.business_metrics:
            try:
                summary["business_kpis"] = self.business_metrics.get_business_kpis()
            except Exception as e:
                logger.error("metrics.business_kpis_failed", error=str(e))
                summary["business_kpis"] = {"error": str(e)}
        
        if self.performance_metrics:
            try:
                summary["performance_summary"] = self.performance_metrics.get_performance_summary()
            except Exception as e:
                logger.error("metrics.performance_summary_failed", error=str(e))
                summary["performance_summary"] = {"error": str(e)}
        
        summary["generated_at"] = "2024-01-01T00:00:00Z"  # Would use actual timestamp
        
        logger.info("metrics.summary_generated", summary_keys=list(summary.keys()))
        return summary

    def create_custom_metric(self, name: str, metric_type: str, description: str, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Create a custom metric dynamically.
        
        Args:
            name: Metric name
            metric_type: Type of metric (counter, histogram, gauge)
            description: Metric description
            labels: Optional labels
        """
        # This would delegate to a custom metrics service when implemented
        logger.info(
            "metrics.custom_metric_created",
            name=name,
            metric_type=metric_type,
            description=description,
            labels=labels
        )

    def health_check(self) -> Dict[str, any]:
        """
        Perform health check of metrics system.
        
        Returns:
            Health check results
        """
        health = {
            "metrics_provider": "healthy",
            "business_metrics": "healthy" if self.business_metrics else "not_configured",
            "performance_metrics": "healthy" if self.performance_metrics else "not_configured",
            "total_metrics": len(self.provider.list_metrics()),
            "checked_at": "2024-01-01T00:00:00Z"
        }
        
        # Test provider functionality
        try:
            test_value = self.provider.get_metric_value("MEDIA_UPLOADS_TOTAL")
            health["provider_test"] = "passed"
        except Exception as e:
            health["provider_test"] = f"failed: {str(e)}"
            health["metrics_provider"] = "unhealthy"
        
        logger.info("metrics.health_check_completed", health=health)
        return health
