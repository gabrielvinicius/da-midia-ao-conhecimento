# src/topic_modeling/infrastructure/metrics.py
import structlog
from prometheus_client import Counter, Histogram, Gauge
from typing import Dict, Any

class PrometheusTopicModelingMetrics:
    """
    Prometheus-based metrics implementation for topic modeling operations.
    Follows SRP - only responsible for metrics collection.
    """
    
    def __init__(self):
        # Operation counters
        self._operation_counter = Counter(
            'topic_modeling_operations_total',
            'Total number of topic modeling operations',
            ['operation', 'provider', 'status']
        )
        
        # Operation duration histogram
        self._operation_duration = Histogram(
            'topic_modeling_operation_duration_seconds',
            'Duration of topic modeling operations in seconds',
            ['operation', 'provider']
        )
        
        # Input text length histogram
        self._input_text_length = Histogram(
            'topic_modeling_input_text_length_chars',
            'Length of input text in characters',
            ['provider']
        )
        
        # Number of topics histogram
        self._num_topics = Histogram(
            'topic_modeling_num_topics',
            'Number of topics identified',
            ['provider']
        )
        
        # Active operations gauge
        self._active_operations = Gauge(
            'topic_modeling_active_operations',
            'Number of active topic modeling operations',
            ['provider']
        )
    
    async def record_operation(
        self, 
        operation: str, 
        provider: str,
        duration: float,
        success: bool,
        input_text_length_chars: int,
        num_topics: int
    ) -> None:
        """Record topic modeling operation metrics."""
        status = "success" if success else "failure"
        
        # Increment operation counter
        self._operation_counter.labels(
            operation=operation,
            provider=provider,
            status=status
        ).inc()
        
        # Record operation duration
        self._operation_duration.labels(
            operation=operation,
            provider=provider
        ).observe(duration)
        
        # Record input/output lengths (only for successful operations)
        if success:
            self._input_text_length.labels(provider=provider).observe(input_text_length_chars)
            self._num_topics.labels(provider=provider).observe(num_topics)


class InMemoryTopicModelingMetrics:
    """
    In-memory metrics implementation for testing.
    Follows SRP and provides same interface.
    """
    
    def __init__(self):
        self._metrics: Dict[str, Dict[str, Any]] = {}
    
    async def record_operation(
        self, 
        operation: str, 
        provider: str,
        duration: float,
        success: bool,
        input_text_length_chars: int,
        num_topics: int
    ) -> None:
        """Record operation metrics in memory."""
        key = f"{operation}_{provider}"
        
        if key not in self._metrics:
            self._metrics[key] = {
                "total_operations": 0,
                "successful_operations": 0,
                "failed_operations": 0,
                "total_duration": 0.0,
                "min_duration": float('inf'),
                "max_duration": 0.0,
                "total_input_text_length_chars": 0,
                "total_num_topics": 0,
            }
        
        metrics = self._metrics[key]
        metrics["total_operations"] += 1
        metrics["total_duration"] += duration
        metrics["min_duration"] = min(metrics["min_duration"], duration)
        metrics["max_duration"] = max(metrics["max_duration"], duration)
        
        if success:
            metrics["successful_operations"] += 1
            metrics["total_input_text_length_chars"] += input_text_length_chars
            metrics["total_num_topics"] += num_topics
        else:
            metrics["failed_operations"] += 1
    
    def get_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all recorded metrics (for testing)."""
        return self._metrics.copy()
    
    def reset_metrics(self) -> None:
        """Reset all metrics (for testing)."""
        self._metrics.clear()


class NoOpTopicModelingMetrics:
    """
    No-operation metrics for when metrics are disabled.
    Follows Null Object pattern.
    """
    
    async def record_operation(
        self, 
        operation: str, 
        provider: str,
        duration: float,
        success: bool,
        input_text_length_chars: int,
        num_topics: int
    ) -> None:
        """No-op implementation."""
        pass
