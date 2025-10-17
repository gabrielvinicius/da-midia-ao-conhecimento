"""
Performance Metrics Service - Single Responsibility: Performance metrics tracking
Follows SRP by handling only performance-related metrics.
"""
from typing import Dict, Any
import structlog

from src.metrics.domain.interfaces import IPerformanceMetrics, IMetricsProvider

logger = structlog.get_logger(__name__)


class PerformanceMetrics(IPerformanceMetrics):
    """
    Service responsible ONLY for performance metrics operations.
    
    Single Responsibility: Handle performance monitoring and optimization metrics.
    Open/Closed: Extensible for new performance metrics.
    Dependency Inversion: Depends on metrics provider abstraction.
    """
    
    def __init__(self, metrics_provider: IMetricsProvider):
        self.metrics_provider = metrics_provider
    
    def track_request_duration(self, endpoint: str, method: str, duration: float, status_code: int) -> None:
        """
        Track HTTP request duration for performance monitoring.
        
        Args:
            endpoint: API endpoint path
            method: HTTP method (GET, POST, etc.)
            duration: Request duration in seconds
            status_code: HTTP status code
        """
        labels = {
            "endpoint": endpoint,
            "method": method,
            "status_code": str(status_code)
        }
        
        # Track request duration
        self.metrics_provider.observe_histogram("REQUEST_DURATION_SECONDS", duration, labels)
        
        # Track request count
        self.metrics_provider.increment_counter("REQUEST_COUNT_TOTAL", labels)
        
        # Track slow requests (> 1 second)
        if duration > 1.0:
            slow_labels = {"endpoint": endpoint, "method": method}
            self.metrics_provider.increment_counter("SLOW_REQUESTS_TOTAL", slow_labels)
        
        # Track error rates
        if status_code >= 400:
            error_labels = {"endpoint": endpoint, "status_code": str(status_code)}
            self.metrics_provider.increment_counter("REQUEST_ERRORS_TOTAL", error_labels)
        
        logger.debug(
            "performance.request_tracked",
            endpoint=endpoint,
            method=method,
            duration=duration,
            status_code=status_code
        )
    
    def track_processing_duration(self, operation: str, duration: float, provider: str) -> None:
        """
        Track processing operation duration for performance analysis.
        
        Args:
            operation: Type of operation (transcription, summarization, etc.)
            duration: Processing duration in seconds
            provider: Service provider used
        """
        labels = {
            "operation": operation,
            "provider": provider
        }
        
        # Track processing duration
        self.metrics_provider.observe_histogram("PROCESSING_DURATION_SECONDS", duration, labels)
        
        # Track processing count
        self.metrics_provider.increment_counter("PROCESSING_COUNT_TOTAL", labels)
        
        # Track long-running operations (> 5 minutes)
        if duration > 300:
            long_labels = {"operation": operation, "provider": provider}
            self.metrics_provider.increment_counter("LONG_PROCESSING_TOTAL", long_labels)
        
        # Calculate and track throughput (operations per minute)
        throughput = 1.0 / (duration / 60) if duration > 0 else 0
        throughput_labels = {"operation": operation}
        self.metrics_provider.observe_histogram("PROCESSING_THROUGHPUT_PER_MINUTE", throughput, throughput_labels)
        
        logger.debug(
            "performance.processing_tracked",
            operation=operation,
            duration=duration,
            provider=provider,
            throughput_per_minute=throughput
        )
    
    def track_queue_size(self, queue_name: str, size: int) -> None:
        """
        Track queue sizes for performance monitoring.
        
        Args:
            queue_name: Name of the queue
            size: Current queue size
        """
        labels = {"queue_name": queue_name}
        
        # Set current queue size
        self.metrics_provider.set_gauge("QUEUE_SIZE_CURRENT", float(size), labels)
        
        # Track queue size changes
        self.metrics_provider.observe_histogram("QUEUE_SIZE_CHANGES", float(size), labels)
        
        # Alert on large queues
        if size > 100:
            self.metrics_provider.increment_counter("LARGE_QUEUE_ALERTS", labels)
        
        logger.debug(
            "performance.queue_size_tracked",
            queue_name=queue_name,
            size=size
        )
    
    def track_resource_usage(self, resource: str, usage: float, unit: str) -> None:
        """
        Track resource usage (CPU, memory, disk, etc.).
        
        Args:
            resource: Resource type (cpu, memory, disk, network)
            usage: Usage value
            unit: Unit of measurement (percent, bytes, etc.)
        """
        labels = {
            "resource": resource,
            "unit": unit
        }
        
        # Track current resource usage
        self.metrics_provider.set_gauge("RESOURCE_USAGE_CURRENT", usage, labels)
        
        # Track resource usage over time
        self.metrics_provider.observe_histogram("RESOURCE_USAGE_HISTORY", usage, labels)
        
        # Alert on high resource usage
        if resource == "cpu" and usage > 80:
            self.metrics_provider.increment_counter("HIGH_CPU_ALERTS", {"threshold": "80"})
        elif resource == "memory" and usage > 85:
            self.metrics_provider.increment_counter("HIGH_MEMORY_ALERTS", {"threshold": "85"})
        
        logger.debug(
            "performance.resource_usage_tracked",
            resource=resource,
            usage=usage,
            unit=unit
        )
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get performance metrics summary.
        
        Returns:
            Dictionary with performance summary
        """
        try:
            # Get current metric values
            total_requests = self.metrics_provider.get_metric_value("REQUEST_COUNT_TOTAL") or 0
            slow_requests = self.metrics_provider.get_metric_value("SLOW_REQUESTS_TOTAL") or 0
            error_requests = self.metrics_provider.get_metric_value("REQUEST_ERRORS_TOTAL") or 0
            processing_count = self.metrics_provider.get_metric_value("PROCESSING_COUNT_TOTAL") or 0
            long_processing = self.metrics_provider.get_metric_value("LONG_PROCESSING_TOTAL") or 0
            
            # Calculate performance indicators
            slow_request_rate = (slow_requests / total_requests * 100) if total_requests > 0 else 0
            error_rate = (error_requests / total_requests * 100) if total_requests > 0 else 0
            long_processing_rate = (long_processing / processing_count * 100) if processing_count > 0 else 0
            
            # Get resource usage
            cpu_usage = self.metrics_provider.get_metric_value("RESOURCE_USAGE_CURRENT", {"resource": "cpu"}) or 0
            memory_usage = self.metrics_provider.get_metric_value("RESOURCE_USAGE_CURRENT", {"resource": "memory"}) or 0
            
            summary = {
                "request_metrics": {
                    "total_requests": total_requests,
                    "slow_requests": slow_requests,
                    "error_requests": error_requests,
                    "slow_request_rate_percent": round(slow_request_rate, 2),
                    "error_rate_percent": round(error_rate, 2)
                },
                "processing_metrics": {
                    "total_processing": processing_count,
                    "long_processing": long_processing,
                    "long_processing_rate_percent": round(long_processing_rate, 2)
                },
                "resource_metrics": {
                    "cpu_usage_percent": cpu_usage,
                    "memory_usage_percent": memory_usage
                },
                "overall_health": self._calculate_health_score(slow_request_rate, error_rate, cpu_usage, memory_usage),
                "calculated_at": "2024-01-01T00:00:00Z"
            }
            
            logger.info("performance.summary_calculated", summary=summary)
            return summary
            
        except Exception as e:
            logger.error("performance.summary_calculation_failed", error=str(e))
            return {
                "error": "Failed to calculate performance summary",
                "calculated_at": "2024-01-01T00:00:00Z"
            }
    
    def track_database_performance(self, operation: str, table: str, duration: float, rows_affected: int) -> None:
        """
        Track database operation performance.
        
        Args:
            operation: Database operation (SELECT, INSERT, UPDATE, DELETE)
            table: Database table name
            duration: Query duration in seconds
            rows_affected: Number of rows affected
        """
        labels = {
            "operation": operation,
            "table": table
        }
        
        # Track query duration
        self.metrics_provider.observe_histogram("DB_QUERY_DURATION_SECONDS", duration, labels)
        
        # Track query count
        self.metrics_provider.increment_counter("DB_QUERY_COUNT_TOTAL", labels)
        
        # Track rows affected
        self.metrics_provider.observe_histogram("DB_ROWS_AFFECTED", float(rows_affected), labels)
        
        # Track slow queries (> 1 second)
        if duration > 1.0:
            slow_labels = {"operation": operation, "table": table}
            self.metrics_provider.increment_counter("DB_SLOW_QUERIES_TOTAL", slow_labels)
        
        logger.debug(
            "performance.database_tracked",
            operation=operation,
            table=table,
            duration=duration,
            rows_affected=rows_affected
        )
    
    def track_cache_performance(self, cache_name: str, operation: str, hit: bool, duration: float) -> None:
        """
        Track cache performance metrics.
        
        Args:
            cache_name: Name of the cache
            operation: Cache operation (get, set, delete)
            hit: Whether it was a cache hit or miss
            duration: Operation duration in seconds
        """
        labels = {
            "cache_name": cache_name,
            "operation": operation,
            "result": "hit" if hit else "miss"
        }
        
        # Track cache operations
        self.metrics_provider.increment_counter("CACHE_OPERATIONS_TOTAL", labels)
        
        # Track cache duration
        self.metrics_provider.observe_histogram("CACHE_OPERATION_DURATION_SECONDS", duration, labels)
        
        # Track cache hit rate
        hit_labels = {"cache_name": cache_name}
        if hit:
            self.metrics_provider.increment_counter("CACHE_HITS_TOTAL", hit_labels)
        else:
            self.metrics_provider.increment_counter("CACHE_MISSES_TOTAL", hit_labels)
        
        logger.debug(
            "performance.cache_tracked",
            cache_name=cache_name,
            operation=operation,
            hit=hit,
            duration=duration
        )
    
    def track_external_api_performance(self, service: str, endpoint: str, duration: float, status_code: int) -> None:
        """
        Track external API call performance.
        
        Args:
            service: External service name
            endpoint: API endpoint
            duration: Request duration in seconds
            status_code: HTTP status code
        """
        labels = {
            "service": service,
            "endpoint": endpoint,
            "status_code": str(status_code)
        }
        
        # Track external API duration
        self.metrics_provider.observe_histogram("EXTERNAL_API_DURATION_SECONDS", duration, labels)
        
        # Track external API calls
        self.metrics_provider.increment_counter("EXTERNAL_API_CALLS_TOTAL", labels)
        
        # Track external API errors
        if status_code >= 400:
            error_labels = {"service": service, "status_code": str(status_code)}
            self.metrics_provider.increment_counter("EXTERNAL_API_ERRORS_TOTAL", error_labels)
        
        # Track slow external calls (> 2 seconds)
        if duration > 2.0:
            slow_labels = {"service": service, "endpoint": endpoint}
            self.metrics_provider.increment_counter("EXTERNAL_API_SLOW_CALLS_TOTAL", slow_labels)
        
        logger.debug(
            "performance.external_api_tracked",
            service=service,
            endpoint=endpoint,
            duration=duration,
            status_code=status_code
        )
    
    def _calculate_health_score(self, slow_request_rate: float, error_rate: float, cpu_usage: float, memory_usage: float) -> str:
        """
        Calculate overall system health score based on performance metrics.
        
        Args:
            slow_request_rate: Percentage of slow requests
            error_rate: Percentage of error requests
            cpu_usage: CPU usage percentage
            memory_usage: Memory usage percentage
            
        Returns:
            Health status string
        """
        # Calculate health score (0-100)
        score = 100
        
        # Deduct points for issues
        score -= min(slow_request_rate * 2, 30)  # Max 30 points for slow requests
        score -= min(error_rate * 3, 40)         # Max 40 points for errors
        score -= min(max(0, cpu_usage - 70), 20) # Deduct for CPU > 70%
        score -= min(max(0, memory_usage - 80), 10) # Deduct for memory > 80%
        
        # Determine health status
        if score >= 90:
            return "excellent"
        elif score >= 75:
            return "good"
        elif score >= 60:
            return "fair"
        elif score >= 40:
            return "poor"
        else:
            return "critical"