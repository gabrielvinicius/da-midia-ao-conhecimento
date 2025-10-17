# src/topic_modeling/infrastructure/metrics.py
"""
Topic modeling metrics implementation - SRP compliance.
"""
from prometheus_client import Counter, Histogram, Gauge
from typing import Dict, Any

from src.topic_modeling.domain.interfaces import TopicModelingMetrics


class PrometheusTopicModelingMetrics(TopicModelingMetrics):
    """
    Prometheus-based metrics implementation for topic modeling operations.
    Follows SRP - only responsible for metrics collection.
    """
    
    def __init__(self):
        # Operation counters
        self._operation_counter = Counter(
            'topic_modeling_operations_total',
            'Total number of topic modeling operations',
            ['operation', 'provider', 'language', 'status']
        )
        
        # Operation duration histogram
        self._operation_duration = Histogram(
            'topic_modeling_operation_duration_seconds',
            'Duration of topic modeling operations in seconds',
            ['operation', 'provider', 'language']
        )
        
        # Text length histogram
        self._text_length_histogram = Histogram(
            'topic_modeling_text_length_chars',
            'Length of processed text in characters',
            ['provider', 'language']
        )
        
        # Number of topics histogram
        self._num_topics_histogram = Histogram(
            'topic_modeling_num_topics',
            'Number of topics extracted',
            ['provider', 'language']
        )
        
        # Coherence score histogram
        self._coherence_score_histogram = Histogram(
            'topic_modeling_coherence_score',
            'Topic coherence scores',
            ['provider', 'language']
        )
        
        # Processing rate histogram
        self._processing_rate_histogram = Histogram(
            'topic_modeling_chars_per_second',
            'Characters processed per second',
            ['provider', 'language']
        )
        
        # Topic quality histogram
        self._topic_quality_histogram = Histogram(
            'topic_modeling_topic_quality',
            'Average topic quality score',
            ['provider', 'language']
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
        language: str,
        duration: float,
        success: bool,
        text_length: int,
        num_topics: int,
        coherence_score: float
    ) -> None:
        """Record topic modeling operation metrics."""
        status = "success" if success else "failure"
        
        # Increment operation counter
        self._operation_counter.labels(
            operation=operation,
            provider=provider,
            language=language,
            status=status
        ).inc()
        
        # Record operation duration
        self._operation_duration.labels(
            operation=operation,
            provider=provider,
            language=language
        ).observe(duration)
        
        # Record metrics for successful operations
        if success:
            if text_length > 0:
                self._text_length_histogram.labels(
                    provider=provider,
                    language=language
                ).observe(text_length)
                
                # Calculate and record processing rate
                if duration > 0:
                    processing_rate = text_length / duration
                    self._processing_rate_histogram.labels(
                        provider=provider,
                        language=language
                    ).observe(processing_rate)
            
            if num_topics > 0:
                self._num_topics_histogram.labels(
                    provider=provider,
                    language=language
                ).observe(num_topics)
            
            if coherence_score > 0:
                self._coherence_score_histogram.labels(
                    provider=provider,
                    language=language
                ).observe(coherence_score)


class InMemoryTopicModelingMetrics(TopicModelingMetrics):
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
        language: str,
        duration: float,
        success: bool,
        text_length: int,
        num_topics: int,
        coherence_score: float
    ) -> None:
        """Record operation metrics in memory."""
        key = f"{operation}_{provider}_{language}"
        
        if key not in self._metrics:
            self._metrics[key] = {
                "total_operations": 0,
                "successful_operations": 0,
                "failed_operations": 0,
                "total_duration": 0.0,
                "min_duration": float('inf'),
                "max_duration": 0.0,
                "total_text_length": 0,
                "total_topics": 0,
                "coherence_scores": [],
                "processing_rates": []
            }
        
        metrics = self._metrics[key]
        metrics["total_operations"] += 1
        metrics["total_duration"] += duration
        metrics["min_duration"] = min(metrics["min_duration"], duration)
        metrics["max_duration"] = max(metrics["max_duration"], duration)
        
        if success:
            metrics["successful_operations"] += 1
            metrics["total_text_length"] += text_length
            metrics["total_topics"] += num_topics
            
            if coherence_score > 0:
                metrics["coherence_scores"].append(coherence_score)
            
            if duration > 0 and text_length > 0:
                processing_rate = text_length / duration
                metrics["processing_rates"].append(processing_rate)
        else:
            metrics["failed_operations"] += 1
    
    def get_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all recorded metrics (for testing)."""
        return self._metrics.copy()
    
    def reset_metrics(self) -> None:
        """Reset all metrics (for testing)."""
        self._metrics.clear()
    
    def get_average_coherence(self, operation: str, provider: str, language: str) -> float:
        """Get average coherence score."""
        key = f"{operation}_{provider}_{language}"
        if key in self._metrics and self._metrics[key]["coherence_scores"]:
            scores = self._metrics[key]["coherence_scores"]
            return sum(scores) / len(scores)
        return 0.0
    
    def get_average_processing_rate(self, operation: str, provider: str, language: str) -> float:
        """Get average processing rate."""
        key = f"{operation}_{provider}_{language}"
        if key in self._metrics and self._metrics[key]["processing_rates"]:
            rates = self._metrics[key]["processing_rates"]
            return sum(rates) / len(rates)
        return 0.0
    
    def get_success_rate(self, operation: str, provider: str, language: str) -> float:
        """Get success rate for operation/provider/language."""
        key = f"{operation}_{provider}_{language}"
        if key in self._metrics:
            metrics = self._metrics[key]
            total = metrics["total_operations"]
            successful = metrics["successful_operations"]
            return successful / total if total > 0 else 0.0
        return 0.0
    
    def get_average_topics_per_operation(self, operation: str, provider: str, language: str) -> float:
        """Get average number of topics per operation."""
        key = f"{operation}_{provider}_{language}"
        if key in self._metrics:
            metrics = self._metrics[key]
            successful = metrics["successful_operations"]
            total_topics = metrics["total_topics"]
            return total_topics / successful if successful > 0 else 0.0
        return 0.0


class NoOpTopicModelingMetrics(TopicModelingMetrics):
    """
    No-operation metrics for when metrics are disabled.
    Follows Null Object pattern.
    """
    
    async def record_operation(
        self, 
        operation: str, 
        provider: str,
        language: str,
        duration: float,
        success: bool,
        text_length: int,
        num_topics: int,
        coherence_score: float
    ) -> None:
        """No-op implementation."""
        pass