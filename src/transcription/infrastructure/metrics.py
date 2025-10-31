# src/transcription/infrastructure/metrics.py
import structlog
from prometheus_client import Counter, Histogram, Gauge
from typing import Dict, Any

class PrometheusTranscriptionMetrics:
    """
    Prometheus-based metrics implementation for transcription operations.
    Follows SRP - only responsible for metrics collection.
    """
    
    def __init__(self):
        # Operation counters
        self._operation_counter = Counter(
            'transcription_operations_total',
            'Total number of transcription operations',
            ['operation', 'provider', 'status']
        )
        
        # Operation duration histogram
        self._operation_duration = Histogram(
            'transcription_operation_duration_seconds',
            'Duration of transcription operations in seconds',
            ['operation', 'provider']
        )
        
        # Input audio length histogram
        self._input_audio_length = Histogram(
            'transcription_input_audio_length_seconds',
            'Length of input audio in seconds',
            ['provider']
        )
        
        # Output text length histogram
        self._output_text_length = Histogram(
            'transcription_output_text_length_chars',
            'Length of output text in characters',
            ['provider']
        )
        
        # Active operations gauge
        self._active_operations = Gauge(
            'transcription_active_operations',
            'Number of active transcription operations',
            ['provider']
        )
    
    async def record_operation(
        self, 
        operation: str, 
        provider: str,
        duration: float,
        success: bool,
        input_audio_length_seconds: float,
        output_text_length_chars: int
    ) -> None:
        """Record transcription operation metrics."""
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
            self._input_audio_length.labels(provider=provider).observe(input_audio_length_seconds)
            self._output_text_length.labels(provider=provider).observe(output_text_length_chars)


class InMemoryTranscriptionMetrics:
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
        input_audio_length_seconds: float,
        output_text_length_chars: int
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
                "total_input_audio_length_seconds": 0.0,
                "total_output_text_length_chars": 0,
            }
        
        metrics = self._metrics[key]
        metrics["total_operations"] += 1
        metrics["total_duration"] += duration
        metrics["min_duration"] = min(metrics["min_duration"], duration)
        metrics["max_duration"] = max(metrics["max_duration"], duration)
        
        if success:
            metrics["successful_operations"] += 1
            metrics["total_input_audio_length_seconds"] += input_audio_length_seconds
            metrics["total_output_text_length_chars"] += output_text_length_chars
        else:
            metrics["failed_operations"] += 1
    
    def get_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all recorded metrics (for testing)."""
        return self._metrics.copy()
    
    def reset_metrics(self) -> None:
        """Reset all metrics (for testing)."""
        self._metrics.clear()


class NoOpTranscriptionMetrics:
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
        input_audio_length_seconds: float,
        output_text_length_chars: int
    ) -> None:
        """No-op implementation."""
        pass
