# src/sentiment_analysis/infrastructure/metrics.py
from typing import Dict, Any

from prometheus_client import Counter, Histogram, Gauge


class PrometheusSentimentMetrics:
    """
    Prometheus-based metrics implementation for sentiment analysis operations.
    Follows SRP - only responsible for metrics collection.
    """
    
    def __init__(self):
        # Operation counters
        self._operation_counter = Counter(
            'sentiment_analysis_operations_total',
            'Total number of sentiment analysis operations',
            ['operation', 'provider', 'status']
        )
        
        # Operation duration histogram
        self._operation_duration = Histogram(
            'sentiment_analysis_operation_duration_seconds',
            'Duration of sentiment analysis operations in seconds',
            ['operation', 'provider']
        )
        
        # Input text length histogram
        self._input_text_length = Histogram(
            'sentiment_analysis_input_text_length_chars',
            'Length of input text in characters',
            ['provider']
        )
        
        # Output score histogram
        self._output_score = Histogram(
            'sentiment_analysis_output_score',
            'Sentiment score output',
            ['provider', 'label']
        )
        
        # Active operations gauge
        self._active_operations = Gauge(
            'sentiment_analysis_active_operations',
            'Number of active sentiment analysis operations',
            ['provider']
        )
    
    async def record_operation(
        self, 
        operation: str, 
        provider: str,
        duration: float,
        success: bool,
        input_text_length_chars: int,
        output_score: float
    ) -> None:
        """Record sentiment analysis operation metrics."""
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
            # Para o score, precisamos de um label para o tipo de sentimento (positivo, negativo, neutro)
            # Isso exigiria que o output_score fosse acompanhado de um label de sentimento
            # Por enquanto, vamos registrar o score sem um label específico aqui, ou assumir um default
            # self._output_score.labels(provider=provider, label="unknown").observe(output_score)


class InMemorySentimentMetrics:
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
        output_score: float
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
                "total_output_score": 0.0,
                "scores": []
            }
        
        metrics = self._metrics[key]
        metrics["total_operations"] += 1
        metrics["total_duration"] += duration
        metrics["min_duration"] = min(metrics["min_duration"], duration)
        metrics["max_duration"] = max(metrics["max_duration"], duration)
        
        if success:
            metrics["successful_operations"] += 1
            metrics["total_input_text_length_chars"] += input_text_length_chars
            metrics["total_output_score"] += output_score
            metrics["scores"].append(output_score)
        else:
            metrics["failed_operations"] += 1
    
    def get_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all recorded metrics (for testing)."""
        return self._metrics.copy()
    
    def reset_metrics(self) -> None:
        """Reset all metrics (for testing)."""
        self._metrics.clear()


class NoOpSentimentMetrics:
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
        output_score: float
    ) -> None:
        """No-op implementation."""
        pass
