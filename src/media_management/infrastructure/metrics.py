# src/media_management/infrastructure/metrics.py
import structlog
from prometheus_client import Counter, Histogram, Gauge
from typing import Dict, Any


class PrometheusMediaMetrics:
    """
    Prometheus-based metrics implementation for media management operations.
    Follows SRP - only responsible for metrics collection.
    """
    
    def __init__(self):
        # Operation counters
        self._operation_counter = Counter(
            'media_management_operations_total',
            'Total number of media management operations',
            ['operation', 'user_id', 'media_type', 'status']
        )
        
        # Operation duration histogram
        self._operation_duration = Histogram(
            'media_management_operation_duration_seconds',
            'Duration of media management operations in seconds',
            ['operation', 'user_id', 'media_type']
        )
        
        # File size histogram
        self._file_size = Histogram(
            'media_management_file_size_bytes',
            'Size of media files in bytes',
            ['user_id', 'media_type']
        )
        
        # Active operations gauge
        self._active_operations = Gauge(
            'media_management_active_operations',
            'Number of active media management operations',
            ['user_id', 'media_type']
        )
    
    async def record_operation(
        self, 
        operation: str, 
        user_id: str,
        media_type: str,
        success: bool,
        duration: float,
        file_size_bytes: int
    ) -> None:
        """Record media management operation metrics."""
        status = "success" if success else "failure"
        
        # Increment operation counter
        self._operation_counter.labels(
            operation=operation,
            user_id=user_id,
            media_type=media_type,
            status=status
        ).inc()
        
        # Record operation duration
        self._operation_duration.labels(
            operation=operation,
            user_id=user_id,
            media_type=media_type
        ).observe(duration)
        
        # Record file size (only for successful operations)
        if success:
            self._file_size.labels(
                user_id=user_id,
                media_type=media_type
            ).observe(file_size_bytes)


class InMemoryMediaMetrics:
    """
    In-memory metrics implementation for testing.
    Follows SRP and provides same interface.
    """
    
    def __init__(self):
        self._metrics: Dict[str, Dict[str, Any]] = {}
    
    async def record_operation(
        self, 
        operation: str, 
        user_id: str,
        media_type: str,
        success: bool,
        duration: float,
        file_size_bytes: int
    ) -> None:
        """Record operation metrics in memory."""
        key = f"{operation}_{user_id}_{media_type}"
        
        if key not in self._metrics:
            self._metrics[key] = {
                "total_operations": 0,
                "successful_operations": 0,
                "failed_operations": 0,
                "total_duration": 0.0,
                "min_duration": float('inf'),
                "max_duration": 0.0,
                "total_file_size_bytes": 0,
            }
        
        metrics = self._metrics[key]
        metrics["total_operations"] += 1
        metrics["total_duration"] += duration
        metrics["min_duration"] = min(metrics["min_duration"], duration)
        metrics["max_duration"] = max(metrics["max_duration"], duration)
        
        if success:
            metrics["successful_operations"] += 1
            metrics["total_file_size_bytes"] += file_size_bytes
        else:
            metrics["failed_operations"] += 1
    
    def get_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all recorded metrics (for testing)."""
        return self._metrics.copy()
    
    def reset_metrics(self) -> None:
        """Reset all metrics (for testing)."""
        self._metrics.clear()


class NoOpMediaMetrics:
    """
    No-operation metrics for when metrics are disabled.
    Follows Null Object pattern.
    """
    
    async def record_operation(
        self, 
        operation: str, 
        user_id: str,
        media_type: str,
        success: bool,
        duration: float,
        file_size_bytes: int
    ) -> None:
        """No-op implementation."""
        pass
