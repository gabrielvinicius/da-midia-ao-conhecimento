"""
Storage Metrics Service - Single Responsibility: Metrics collection.
Follows SRP by handling only metrics-related operations for storage.
"""
import time
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime
import structlog

from src.storage.domain.interfaces import IStorageMetricsService
from src.shared.monitoring.metrics_collector import MetricsCollector

logger = structlog.get_logger(__name__)


class StorageMetricsService(IStorageMetricsService):
    """
    Storage metrics service following SRP.
    Single responsibility: Collect and report storage operation metrics.
    """
    
    def __init__(self, metrics_collector: MetricsCollector):
        self._metrics_collector = metrics_collector
        self._operation_start_times: Dict[UUID, float] = {}
    
    def record_upload_start(self, file_id: UUID, file_size: int, provider: str) -> None:
        """Record start of file upload."""
        self._operation_start_times[file_id] = time.time()
        
        self._metrics_collector.record_counter(
            "storage_upload_started_total",
            labels={"provider": provider}
        )
        
        self._metrics_collector.record_gauge(
            "storage_file_size_bytes",
            file_size,
            labels={"provider": provider, "operation": "upload"}
        )
        
        logger.debug(
            "storage.metrics.upload_started",
            file_id=str(file_id),
            file_size=file_size,
            provider=provider
        )
    
    def record_upload_success(self, file_id: UUID, duration: float, provider: str) -> None:
        """Record successful file upload."""
        # Calculate duration if not provided
        if duration == 0:
            start_time = self._operation_start_times.pop(file_id, None)
            duration = time.time() - start_time if start_time else 0
        else:
            self._operation_start_times.pop(file_id, None)
        
        self._metrics_collector.record_counter(
            "storage_upload_success_total",
            labels={"provider": provider}
        )
        
        self._metrics_collector.record_histogram(
            "storage_upload_duration_seconds",
            duration,
            labels={"provider": provider, "status": "success"}
        )
        
        logger.info(
            "storage.metrics.upload_success",
            file_id=str(file_id),
            duration=duration,
            provider=provider
        )
    
    def record_upload_failure(self, file_id: UUID, error: str, provider: str) -> None:
        """Record failed file upload."""
        start_time = self._operation_start_times.pop(file_id, None)
        duration = time.time() - start_time if start_time else 0
        
        error_category = self._categorize_error(error)
        
        self._metrics_collector.record_counter(
            "storage_upload_failure_total",
            labels={"provider": provider, "error_type": error_category}
        )
        
        self._metrics_collector.record_histogram(
            "storage_upload_duration_seconds",
            duration,
            labels={"provider": provider, "status": "failure"}
        )
        
        logger.warning(
            "storage.metrics.upload_failure",
            file_id=str(file_id),
            error=error,
            error_category=error_category,
            duration=duration,
            provider=provider
        )
    
    def record_download_success(self, file_id: UUID, duration: float, provider: str) -> None:
        """Record successful file download."""
        self._metrics_collector.record_counter(
            "storage_download_success_total",
            labels={"provider": provider}
        )
        
        self._metrics_collector.record_histogram(
            "storage_download_duration_seconds",
            duration,
            labels={"provider": provider, "status": "success"}
        )
        
        logger.info(
            "storage.metrics.download_success",
            file_id=str(file_id),
            duration=duration,
            provider=provider
        )
    
    def record_storage_utilization(self, provider: str, used_bytes: int, total_bytes: int) -> None:
        """Record storage utilization metrics."""
        utilization_percentage = (used_bytes / total_bytes) * 100 if total_bytes > 0 else 0
        
        self._metrics_collector.record_gauge(
            "storage_utilization_percentage",
            utilization_percentage,
            labels={"provider": provider}
        )
        
        self._metrics_collector.record_gauge(
            "storage_used_bytes",
            used_bytes,
            labels={"provider": provider}
        )
        
        self._metrics_collector.record_gauge(
            "storage_total_bytes",
            total_bytes,
            labels={"provider": provider}
        )
        
        logger.info(
            "storage.metrics.utilization_recorded",
            provider=provider,
            used_gb=used_bytes / (1024**3),
            total_gb=total_bytes / (1024**3),
            utilization_percentage=utilization_percentage
        )
    
    def get_storage_stats(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """Get storage statistics."""
        stats = {
            "timestamp": datetime.utcnow().isoformat(),
            "provider_filter": provider,
            "upload_metrics": {
                "total_uploads": self._get_metric_count("storage_upload_success_total", provider),
                "failed_uploads": self._get_metric_count("storage_upload_failure_total", provider),
                "active_uploads": len([k for k in self._operation_start_times.keys()]),
                "success_rate": self._calculate_success_rate("upload", provider)
            },
            "download_metrics": {
                "total_downloads": self._get_metric_count("storage_download_success_total", provider),
                "success_rate": self._calculate_success_rate("download", provider)
            },
            "performance_metrics": {
                "avg_upload_duration": self._get_avg_duration("upload", provider),
                "avg_download_duration": self._get_avg_duration("download", provider)
            }
        }
        
        if provider:
            stats["provider"] = provider
            utilization = self._get_storage_utilization(provider)
            if utilization:
                stats["storage_utilization"] = utilization
        
        logger.debug(
            "storage.metrics.stats_generated",
            provider=provider,
            total_uploads=stats["upload_metrics"]["total_uploads"]
        )
        
        return stats
    
    def _categorize_error(self, error: str) -> str:
        """Categorize error for metrics."""
        error_lower = error.lower()
        
        if "permission" in error_lower or "access" in error_lower:
            return "permission_error"
        elif "network" in error_lower or "connection" in error_lower:
            return "network_error"
        elif "not found" in error_lower or "404" in error_lower:
            return "not_found_error"
        elif "timeout" in error_lower:
            return "timeout_error"
        elif "space" in error_lower or "quota" in error_lower:
            return "quota_error"
        elif "validation" in error_lower:
            return "validation_error"
        else:
            return "unknown_error"
    
    def _get_metric_count(self, metric_name: str, provider: Optional[str] = None) -> int:
        """Get metric count (placeholder implementation)."""
        # In real implementation, this would query the metrics backend
        return 0
    
    def _calculate_success_rate(self, operation: str, provider: Optional[str] = None) -> float:
        """Calculate success rate for operation."""
        success_count = self._get_metric_count(f"storage_{operation}_success_total", provider)
        failure_count = self._get_metric_count(f"storage_{operation}_failure_total", provider)
        total = success_count + failure_count
        
        if total == 0:
            return 100.0
        
        return round((success_count / total) * 100, 2)
    
    def _get_avg_duration(self, operation: str, provider: Optional[str] = None) -> float:
        """Get average duration for operation."""
        # Placeholder implementation
        return 2.5  # seconds
    
    def _get_storage_utilization(self, provider: str) -> Optional[Dict[str, Any]]:
        """Get storage utilization for provider."""
        # Placeholder implementation
        return {
            "used_percentage": 45.2,
            "used_gb": 123.5,
            "total_gb": 273.1
        }