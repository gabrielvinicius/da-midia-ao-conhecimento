"""
Consolidated Media Metrics Service
Consolidates: MediaMetricsService, EnhancedMediaMetricsService
"""
import time
import structlog
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timedelta

from src.shared.monitoring.metrics_collector import MetricsCollector

logger = structlog.get_logger(__name__)


class MediaMetricsService:
    """
    Consolidated service for all media-related metrics.
    Handles upload metrics, processing metrics, storage metrics, and performance tracking.
    """
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self._upload_start_times: Dict[UUID, float] = {}
        self._processing_start_times: Dict[UUID, float] = {}

    # === UPLOAD METRICS ===
    
    def record_upload_start(self, media_id: UUID, file_size: int) -> None:
        """Record start of media upload."""
        self._upload_start_times[media_id] = time.time()
        
        self.metrics_collector.record_counter(
            "media_upload_started_total",
            labels={"media_id": str(media_id)}
        )
        
        self.metrics_collector.record_gauge(
            "media_upload_file_size_bytes",
            file_size,
            labels={"media_id": str(media_id)}
        )
        
        logger.info("media.upload.started", media_id=str(media_id), file_size=file_size)
    
    def record_upload_success(self, media_id: UUID, duration: float, provider: str, file_size: int) -> None:
        """Record successful upload."""
        self.metrics_collector.record_counter(
            "media_upload_completed_total",
            labels={"status": "success", "provider": provider}
        )
        
        self.metrics_collector.record_histogram(
            "media_upload_duration_seconds",
            duration,
            labels={"provider": provider, "status": "success"}
        )
        
        # Calculate upload speed
        upload_speed = file_size / duration if duration > 0 else 0
        self.metrics_collector.record_gauge(
            "media_upload_speed_bytes_per_second",
            upload_speed,
            labels={"provider": provider}
        )
        
        # Calculate efficiency ratio
        efficiency_ratio = file_size / (duration * 1024 * 1024) if duration > 0 else 0  # MB/s
        self.metrics_collector.record_gauge(
            "media_upload_efficiency_mb_per_second",
            efficiency_ratio,
            labels={"provider": provider}
        )
        
        logger.info(
            "media.upload.completed",
            media_id=str(media_id),
            duration=duration,
            provider=provider,
            file_size=file_size,
            upload_speed=upload_speed
        )
    
    def record_upload_failure(self, media_id: UUID, error: str, provider: str) -> None:
        """Record failed upload."""
        start_time = self._upload_start_times.pop(media_id, None)
        duration = time.time() - start_time if start_time else 0
        
        error_category = self._categorize_error(error)
        
        self.metrics_collector.record_counter(
            "media_upload_completed_total",
            labels={"status": "failure", "provider": provider, "error_type": error_category}
        )
        
        self.metrics_collector.record_histogram(
            "media_upload_duration_seconds",
            duration,
            labels={"provider": provider, "status": "failure"}
        )
        
        logger.error(
            "media.upload.failed",
            media_id=str(media_id),
            error=error,
            error_category=error_category,
            duration=duration,
            provider=provider
        )

    # === PROCESSING METRICS ===
    
    def record_processing_start(self, media_id: UUID, media_type: str) -> None:
        """Record start of media processing."""
        self._processing_start_times[media_id] = time.time()
        
        self.metrics_collector.record_counter(
            "media_processing_started_total",
            labels={"media_type": media_type}
        )
        
        logger.info("media.processing.started", media_id=str(media_id), media_type=media_type)
    
    def record_processing_success(self, media_id: UUID, media_type: str, stage: str) -> None:
        """Record successful processing stage."""
        start_time = self._processing_start_times.get(media_id)
        duration = time.time() - start_time if start_time else 0
        
        self.metrics_collector.record_counter(
            "media_processing_stage_completed_total",
            labels={"status": "success", "media_type": media_type, "stage": stage}
        )
        
        self.metrics_collector.record_histogram(
            "media_processing_stage_duration_seconds",
            duration,
            labels={"media_type": media_type, "stage": stage, "status": "success"}
        )
        
        logger.info(
            "media.processing.stage_completed",
            media_id=str(media_id),
            media_type=media_type,
            stage=stage,
            duration=duration
        )
    
    def record_processing_failure(self, media_id: UUID, media_type: str, stage: str, error: str) -> None:
        """Record failed processing stage."""
        start_time = self._processing_start_times.pop(media_id, None)
        duration = time.time() - start_time if start_time else 0
        
        error_category = self._categorize_error(error)
        
        self.metrics_collector.record_counter(
            "media_processing_stage_completed_total",
            labels={"status": "failure", "media_type": media_type, "stage": stage, "error_type": error_category}
        )
        
        self.metrics_collector.record_histogram(
            "media_processing_stage_duration_seconds",
            duration,
            labels={"media_type": media_type, "stage": stage, "status": "failure"}
        )
        
        logger.error(
            "media.processing.stage_failed",
            media_id=str(media_id),
            media_type=media_type,
            stage=stage,
            error=error,
            error_category=error_category,
            duration=duration
        )

    # === STORAGE METRICS ===
    
    def record_storage_operation(self, operation: str, provider: str, success: bool, duration: float, file_size: Optional[int] = None) -> None:
        """Record storage operation metrics."""
        status = "success" if success else "failure"
        
        self.metrics_collector.record_counter(
            "media_storage_operations_total",
            labels={"operation": operation, "provider": provider, "status": status}
        )
        
        self.metrics_collector.record_histogram(
            "media_storage_operation_duration_seconds",
            duration,
            labels={"operation": operation, "provider": provider, "status": status}
        )
        
        if file_size is not None:
            self.metrics_collector.record_gauge(
                "media_storage_file_size_bytes",
                file_size,
                labels={"operation": operation, "provider": provider}
            )
            
            # Calculate throughput
            throughput = file_size / duration if duration > 0 else 0
            self.metrics_collector.record_gauge(
                "media_storage_throughput_bytes_per_second",
                throughput,
                labels={"operation": operation, "provider": provider}
            )

    # === PERFORMANCE METRICS ===
    
    def record_media_access(self, media_id: UUID, user_id: str, access_type: str) -> None:
        """Record media access patterns."""
        self.metrics_collector.record_counter(
            "media_access_total",
            labels={"access_type": access_type}
        )
        
        logger.debug("media.accessed", media_id=str(media_id), user_id=user_id, access_type=access_type)
    
    def record_media_deletion(self, media_id: UUID, user_id: str, reason: str = "user_request") -> None:
        """Record media deletion."""
        self.metrics_collector.record_counter(
            "media_deletion_total",
            labels={"reason": reason}
        )
        
        logger.info("media.deleted", media_id=str(media_id), user_id=user_id, reason=reason)
    
    def record_reprocessing_request(self, media_id: UUID, trigger: str = "user_request") -> None:
        """Record media reprocessing request."""
        self.metrics_collector.record_counter(
            "media_reprocessing_requests_total",
            labels={"trigger": trigger}
        )
        
        logger.info("media.reprocessing.requested", media_id=str(media_id), trigger=trigger)

    # === SYSTEM HEALTH METRICS ===
    
    def record_queue_metrics(self, queue_name: str, queue_size: int, processing_time: float) -> None:
        """Record media processing queue metrics."""
        self.metrics_collector.record_gauge(
            "media_queue_size",
            queue_size,
            labels={"queue": queue_name}
        )
        
        self.metrics_collector.record_histogram(
            "media_queue_processing_time_seconds",
            processing_time,
            labels={"queue": queue_name}
        )
    
    def record_resource_usage(self, resource_type: str, usage_percentage: float, threshold: float = 80.0) -> None:
        """Record resource usage metrics."""
        self.metrics_collector.record_gauge(
            "media_resource_usage_percentage",
            usage_percentage,
            labels={"resource_type": resource_type}
        )
        
        if usage_percentage > threshold:
            self.metrics_collector.record_counter(
                "media_resource_alerts_total",
                labels={"resource_type": resource_type, "alert_type": "high_usage"}
            )
            
            logger.warning(
                "media.resource.high_usage",
                resource_type=resource_type,
                usage_percentage=usage_percentage,
                threshold=threshold
            )

    # === PRIVATE METHODS ===
    
    def _categorize_error(self, error: str) -> str:
        """Categorize error for metrics labeling."""
        error_lower = error.lower()
        
        if "validation" in error_lower or "invalid" in error_lower:
            return "validation_error"
        elif "timeout" in error_lower:
            return "timeout_error"
        elif "size" in error_lower or "limit" in error_lower:
            return "size_error"
        elif "permission" in error_lower or "unauthorized" in error_lower:
            return "permission_error"
        elif "storage" in error_lower or "disk" in error_lower:
            return "storage_error"
        elif "network" in error_lower or "connection" in error_lower:
            return "network_error"
        elif "format" in error_lower or "codec" in error_lower:
            return "format_error"
        else:
            return "unknown_error"
    
    def cleanup_old_timers(self, max_age_minutes: int = 60) -> None:
        """Clean up old timer entries to prevent memory leaks."""
        cutoff_time = time.time() - (max_age_minutes * 60)
        
        # Clean upload timers
        expired_upload_keys = [
            key for key, start_time in self._upload_start_times.items()
            if start_time < cutoff_time
        ]
        for key in expired_upload_keys:
            self._upload_start_times.pop(key, None)
        
        # Clean processing timers
        expired_processing_keys = [
            key for key, start_time in self._processing_start_times.items()
            if start_time < cutoff_time
        ]
        for key in expired_processing_keys:
            self._processing_start_times.pop(key, None)
        
        if expired_upload_keys or expired_processing_keys:
            logger.debug(
                "media.metrics.cleanup",
                expired_upload_timers=len(expired_upload_keys),
                expired_processing_timers=len(expired_processing_keys)
            )