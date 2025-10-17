"""
Enhanced Media Metrics Service - Single Responsibility: Metrics collection.
Follows SRP by handling only metrics-related operations for media management.
"""
import time
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timedelta
import structlog

from src.media_management.domain.interfaces import IMediaMetricsService
from src.shared.monitoring.metrics_collector import MetricsCollector

logger = structlog.get_logger(__name__)


class EnhancedMediaMetricsService(IMediaMetricsService):
    """
    Enhanced media metrics service following SRP.
    Single responsibility: Collect and report media processing metrics.
    """
    
    def __init__(self, metrics_collector: MetricsCollector):
        self._metrics_collector = metrics_collector
        self._upload_start_times: Dict[UUID, float] = {}
        self._processing_start_times: Dict[UUID, float] = {}
    
    def record_upload_success(self, media_id: UUID, duration: float, provider: str) -> None:
        """
        Record successful upload metrics.
        
        Args:
            media_id: Media ID that was uploaded
            duration: Upload duration in seconds
            provider: Storage provider used
        """
        # Remove from tracking
        self._upload_start_times.pop(media_id, None)
        
        # Record success metrics
        self._metrics_collector.record_counter(
            "media_upload_success_total",
            labels={"provider": provider}
        )
        
        self._metrics_collector.record_histogram(
            "media_upload_duration_seconds",
            duration,
            labels={"provider": provider, "status": "success"}
        )
        
        logger.info(
            "media.metrics.upload_success",
            media_id=str(media_id),
            provider=provider,
            duration=duration
        )
    
    def record_upload_failure(self, media_id: UUID, error: str) -> None:
        """
        Record upload failure metrics.
        
        Args:
            media_id: Media ID that failed
            error: Error message
        """
        # Calculate duration if we have start time
        start_time = self._upload_start_times.pop(media_id, None)
        duration = time.time() - start_time if start_time else 0
        
        error_category = self._categorize_upload_error(error)
        
        # Record failure metrics
        self._metrics_collector.record_counter(
            "media_upload_failure_total",
            labels={"error_type": error_category}
        )
        
        self._metrics_collector.record_histogram(
            "media_upload_duration_seconds",
            duration,
            labels={"status": "failure", "error_type": error_category}
        )
        
        logger.warning(
            "media.metrics.upload_failure",
            media_id=str(media_id),
            error=error,
            error_category=error_category,
            duration=duration
        )
    
    def record_processing_duration(self, media_id: UUID, duration: float, operation: str) -> None:
        """
        Record processing duration metrics.
        
        Args:
            media_id: Media ID being processed
            duration: Processing duration in seconds
            operation: Type of operation (transcription, summarization, etc.)
        """
        self._metrics_collector.record_histogram(
            "media_processing_duration_seconds",
            duration,
            labels={"operation": operation}
        )
        
        self._metrics_collector.record_counter(
            "media_processing_operations_total",
            labels={"operation": operation}
        )
        
        logger.info(
            "media.metrics.processing_duration",
            media_id=str(media_id),
            operation=operation,
            duration=duration
        )
    
    def get_upload_stats(self, time_range: str) -> dict:
        """
        Get upload statistics.
        
        Args:
            time_range: Time range for stats (hour, day, week)
            
        Returns:
            Dict with upload statistics
        """
        # This would typically query stored metrics
        # For now, return basic structure
        
        stats = {
            "time_range": time_range,
            "generated_at": datetime.utcnow().isoformat(),
            "upload_summary": {
                "total_uploads": self._get_metric_count("media_upload_success_total"),
                "failed_uploads": self._get_metric_count("media_upload_failure_total"),
                "active_uploads": len(self._upload_start_times),
                "success_rate": self._calculate_upload_success_rate()
            },
            "provider_breakdown": {
                "s3_uploads": self._get_metric_count("media_upload_success_total", {"provider": "s3"}),
                "local_uploads": self._get_metric_count("media_upload_success_total", {"provider": "local"}),
                "azure_uploads": self._get_metric_count("media_upload_success_total", {"provider": "azure"})
            },
            "error_analysis": {
                "validation_errors": self._get_metric_count("media_upload_failure_total", {"error_type": "validation_error"}),
                "storage_errors": self._get_metric_count("media_upload_failure_total", {"error_type": "storage_error"}),
                "network_errors": self._get_metric_count("media_upload_failure_total", {"error_type": "network_error"}),
                "permission_errors": self._get_metric_count("media_upload_failure_total", {"error_type": "permission_error"})
            },
            "performance_metrics": {
                "average_upload_duration": self._calculate_average_upload_duration(),
                "fastest_upload": self._get_fastest_upload_time(),
                "slowest_upload": self._get_slowest_upload_time(),
                "throughput_mbps": self._calculate_average_throughput()
            }
        }
        
        logger.info(
            "media.metrics.stats_generated",
            time_range=time_range,
            total_uploads=stats["upload_summary"]["total_uploads"]
        )
        
        return stats
    
    def record_upload_start(self, media_id: UUID) -> None:
        """
        Record upload start for duration tracking.
        
        Args:
            media_id: Media ID starting upload
        """
        self._upload_start_times[media_id] = time.time()
        
        self._metrics_collector.record_counter(
            "media_upload_started_total"
        )
        
        logger.debug(
            "media.metrics.upload_started",
            media_id=str(media_id)
        )
    
    def record_file_size_metrics(self, media_id: UUID, file_size: int, media_type: str) -> None:
        """
        Record file size metrics.
        
        Args:
            media_id: Media ID
            file_size: File size in bytes
            media_type: Type of media (video, audio, image)
        """
        # Convert to MB for easier reading
        file_size_mb = file_size / (1024 * 1024)
        
        self._metrics_collector.record_gauge(
            "media_file_size_mb",
            file_size_mb,
            labels={"media_type": media_type}
        )
        
        self._metrics_collector.record_histogram(
            "media_file_size_distribution_mb",
            file_size_mb,
            labels={"media_type": media_type}
        )
        
        logger.debug(
            "media.metrics.file_size_recorded",
            media_id=str(media_id),
            file_size_mb=file_size_mb,
            media_type=media_type
        )
    
    def record_storage_utilization(self, provider: str, used_space_gb: float, total_space_gb: float) -> None:
        """
        Record storage utilization metrics.
        
        Args:
            provider: Storage provider name
            used_space_gb: Used space in GB
            total_space_gb: Total available space in GB
        """
        utilization_percentage = (used_space_gb / total_space_gb) * 100 if total_space_gb > 0 else 0
        
        self._metrics_collector.record_gauge(
            "storage_utilization_percentage",
            utilization_percentage,
            labels={"provider": provider}
        )
        
        self._metrics_collector.record_gauge(
            "storage_used_space_gb",
            used_space_gb,
            labels={"provider": provider}
        )
        
        self._metrics_collector.record_gauge(
            "storage_total_space_gb",
            total_space_gb,
            labels={"provider": provider}
        )
        
        logger.info(
            "media.metrics.storage_utilization",
            provider=provider,
            used_space_gb=used_space_gb,
            total_space_gb=total_space_gb,
            utilization_percentage=utilization_percentage
        )
    
    def _categorize_upload_error(self, error: str) -> str:
        """Categorize upload error for metrics."""
        error_lower = error.lower()
        
        if "validation" in error_lower or "invalid" in error_lower:
            return "validation_error"
        elif "storage" in error_lower or "bucket" in error_lower or "container" in error_lower:
            return "storage_error"
        elif "network" in error_lower or "connection" in error_lower or "timeout" in error_lower:
            return "network_error"
        elif "permission" in error_lower or "access" in error_lower or "forbidden" in error_lower:
            return "permission_error"
        elif "space" in error_lower or "quota" in error_lower or "limit" in error_lower:
            return "quota_error"
        else:
            return "unknown_error"
    
    def _get_metric_count(self, metric_name: str, labels: dict = None) -> int:
        """Get metric count (placeholder implementation)."""
        # In real implementation, this would query the metrics backend
        return 0
    
    def _calculate_upload_success_rate(self) -> float:
        """Calculate upload success rate."""
        total_success = self._get_metric_count("media_upload_success_total")
        total_failure = self._get_metric_count("media_upload_failure_total")
        total = total_success + total_failure
        
        if total == 0:
            return 100.0
        
        return round((total_success / total) * 100, 2)
    
    def _calculate_average_upload_duration(self) -> float:
        """Calculate average upload duration."""
        # Placeholder implementation
        return 15.5  # seconds
    
    def _get_fastest_upload_time(self) -> float:
        """Get fastest upload time."""
        # Placeholder implementation
        return 2.1  # seconds
    
    def _get_slowest_upload_time(self) -> float:
        """Get slowest upload time."""
        # Placeholder implementation
        return 45.8  # seconds
    
    def _calculate_average_throughput(self) -> float:
        """Calculate average throughput in Mbps."""
        # Placeholder implementation
        return 12.5  # Mbps