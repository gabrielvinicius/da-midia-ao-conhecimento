# src/text_processing/infrastructure/metrics.py
"""
Text processing metrics implementation - SRP compliance.
"""
from prometheus_client import Counter, Histogram, Gauge
from typing import Dict, Any

class PrometheusTextProcessingMetrics:
    """
    Prometheus-based metrics implementation for text processing operations.
    Follows SRP - only responsible for metrics collection.
    """
    
    def __init__(self):
        # Operation counters
        self._operation_counter = Counter(
            'text_processing_operations_total',
            'Total number of text processing operations',
            ['operation', 'format_type', 'status']
        )
        
        # Operation duration histogram
        self._operation_duration = Histogram(
            'text_processing_operation_duration_seconds',
            'Duration of text processing operations in seconds',
            ['operation', 'format_type']
        )
        
        # File size histograms
        self._file_size_histogram = Histogram(
            'text_processing_file_size_bytes',
            'Size of processed files in bytes',
            ['format_type']
        )
        
        # Text length histograms
        self._text_length_histogram = Histogram(
            'text_processing_text_length_chars',
            'Length of extracted text in characters',
            ['format_type']
        )
        
        # Extraction ratio gauge
        self._extraction_ratio = Histogram(
            'text_processing_extraction_ratio',
            'Ratio of extracted text length to file size',
            ['format_type']
        )
        
        # Active operations gauge
        self._active_operations = Gauge(
            'text_processing_active_operations',
            'Number of active text processing operations',
            ['format_type']
        )
    
    async def record_operation(
        self, 
        operation: str, 
        format_type: str,
        duration: float,
        success: bool,
        file_size: int,
        text_length: int
    ) -> None:
        """Record text processing operation metrics."""
        status = "success" if success else "failure"
        
        # Increment operation counter
        self._operation_counter.labels(
            operation=operation,
            format_type=format_type,
            status=status
        ).inc()
        
        # Record operation duration
        self._operation_duration.labels(
            operation=operation,
            format_type=format_type
        ).observe(duration)
        
        # Record file and text metrics (only for successful operations)
        if success and file_size > 0 and text_length > 0:
            self._file_size_histogram.labels(format_type=format_type).observe(file_size)
            self._text_length_histogram.labels(format_type=format_type).observe(text_length)
            
            # Calculate and record extraction ratio
            extraction_ratio = text_length / file_size if file_size > 0 else 0
            self._extraction_ratio.labels(format_type=format_type).observe(extraction_ratio)


class InMemoryTextProcessingMetrics:
    """
    In-memory metrics implementation for testing.
    Follows SRP and provides same interface.
    """
    
    def __init__(self):
        self._metrics: Dict[str, Dict[str, Any]] = {}
    
    async def record_operation(
        self, 
        operation: str, 
        format_type: str,
        duration: float,
        success: bool,
        file_size: int,
        text_length: int
    ) -> None:
        """Record operation metrics in memory."""
        key = f"{operation}_{format_type}"
        
        if key not in self._metrics:
            self._metrics[key] = {
                "total_operations": 0,
                "successful_operations": 0,
                "failed_operations": 0,
                "total_duration": 0.0,
                "min_duration": float('inf'),
                "max_duration": 0.0,
                "total_file_size": 0,
                "total_text_length": 0,
                "extraction_ratios": []
            }
        
        metrics = self._metrics[key]
        metrics["total_operations"] += 1
        metrics["total_duration"] += duration
        metrics["min_duration"] = min(metrics["min_duration"], duration)
        metrics["max_duration"] = max(metrics["max_duration"], duration)
        
        if success:
            metrics["successful_operations"] += 1
            metrics["total_file_size"] += file_size
            metrics["total_text_length"] += text_length
            
            if file_size > 0:
                extraction_ratio = text_length / file_size
                metrics["extraction_ratios"].append(extraction_ratio)
        else:
            metrics["failed_operations"] += 1
    
    def get_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all recorded metrics (for testing)."""
        return self._metrics.copy()
    
    def reset_metrics(self) -> None:
        """Reset all metrics (for testing)."""
        self._metrics.clear()
    
    def get_average_extraction_ratio(self, operation: str, format_type: str) -> float:
        """Get average extraction ratio for operation/format."""
        key = f"{operation}_{format_type}"
        if key in self._metrics and self._metrics[key]["extraction_ratios"]:
            ratios = self._metrics[key]["extraction_ratios"]
            return sum(ratios) / len(ratios)
        return 0.0
    
    def get_success_rate(self, operation: str, format_type: str) -> float:
        """Get success rate for operation/format."""
        key = f"{operation}_{format_type}"
        if key in self._metrics:
            metrics = self._metrics[key]
            total = metrics["total_operations"]
            successful = metrics["successful_operations"]
            return successful / total if total > 0 else 0.0
        return 0.0


class NoOpTextProcessingMetrics:
    """
    No-operation metrics for when metrics are disabled.
    Follows Null Object pattern.
    """
    
    async def record_operation(
        self, 
        operation: str, 
        format_type: str,
        duration: float,
        success: bool,
        file_size: int,
        text_length: int
    ) -> None:
        """No-op implementation."""
        pass