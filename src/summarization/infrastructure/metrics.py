# src/summarization/infrastructure/metrics.py
"""
Summarization metrics implementation - SRP compliance.
"""
from prometheus_client import Counter, Histogram, Gauge
from typing import Dict, Any

from src.summarization.domain.interfaces import SummaryMetrics


class PrometheusSummaryMetrics(SummaryMetrics):
    """
    Prometheus-based metrics implementation for summarization operations.
    Follows SRP - only responsible for metrics collection.
    """
    
    def __init__(self):
        # Operation counters
        self._operation_counter = Counter(
            'summarization_operations_total',
            'Total number of summarization operations',
            ['operation', 'provider', 'status']
        )
        
        # Operation duration histogram
        self._operation_duration = Histogram(
            'summarization_operation_duration_seconds',
            'Duration of summarization operations in seconds',
            ['operation', 'provider']
        )
        
        # Text length histograms
        self._input_length_histogram = Histogram(
            'summarization_input_length_chars',
            'Length of input text in characters',
            ['provider']
        )
        
        self._output_length_histogram = Histogram(
            'summarization_output_length_chars',
            'Length of output summary in characters',
            ['provider']
        )
        
        # Compression ratio gauge
        self._compression_ratio = Histogram(
            'summarization_compression_ratio',
            'Ratio of output length to input length',
            ['provider']
        )
        
        # Active operations gauge
        self._active_operations = Gauge(
            'summarization_active_operations',
            'Number of active summarization operations',
            ['provider']
        )
    
    async def record_operation(
        self, 
        operation: str, 
        provider: str,
        duration: float,
        success: bool,
        input_length: int,
        output_length: int
    ) -> None:
        """Record summarization operation metrics."""
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
        
        # Record text lengths (only for successful operations)
        if success and input_length > 0 and output_length > 0:
            self._input_length_histogram.labels(provider=provider).observe(input_length)
            self._output_length_histogram.labels(provider=provider).observe(output_length)
            
            # Calculate and record compression ratio
            compression_ratio = output_length / input_length if input_length > 0 else 0
            self._compression_ratio.labels(provider=provider).observe(compression_ratio)


class InMemorySummaryMetrics(SummaryMetrics):
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
        input_length: int,
        output_length: int
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
                "total_input_length": 0,
                "total_output_length": 0,
                "compression_ratios": []
            }
        
        metrics = self._metrics[key]
        metrics["total_operations"] += 1
        metrics["total_duration"] += duration
        metrics["min_duration"] = min(metrics["min_duration"], duration)
        metrics["max_duration"] = max(metrics["max_duration"], duration)
        
        if success:
            metrics["successful_operations"] += 1
            metrics["total_input_length"] += input_length
            metrics["total_output_length"] += output_length
            
            if input_length > 0:
                compression_ratio = output_length / input_length
                metrics["compression_ratios"].append(compression_ratio)
        else:
            metrics["failed_operations"] += 1
    
    def get_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all recorded metrics (for testing)."""
        return self._metrics.copy()
    
    def reset_metrics(self) -> None:
        """Reset all metrics (for testing)."""
        self._metrics.clear()
    
    def get_average_compression_ratio(self, operation: str, provider: str) -> float:
        """Get average compression ratio for operation/provider."""
        key = f"{operation}_{provider}"
        if key in self._metrics and self._metrics[key]["compression_ratios"]:
            ratios = self._metrics[key]["compression_ratios"]
            return sum(ratios) / len(ratios)
        return 0.0


class NoOpSummaryMetrics(SummaryMetrics):
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
        input_length: int,
        output_length: int
    ) -> None:
        """No-op implementation."""
        pass