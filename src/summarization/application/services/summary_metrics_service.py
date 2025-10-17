"""
Summary Metrics Service - Single Responsibility: Metrics collection and reporting.
Follows SRP by handling only metrics-related operations.
"""
import time
from typing import Dict, Any, Optional
from uuid import UUID
import structlog

from src.summarization.domain.interfaces import ISummaryMetricsService
from src.shared.monitoring.metrics_collector import MetricsCollector

logger = structlog.get_logger(__name__)


class SummaryMetricsService(ISummaryMetricsService):
    """
    Handles summary processing metrics following SRP.
    Single responsibility: Collect and report summary metrics.
    """
    
    def __init__(self, metrics_collector: MetricsCollector):
        self._metrics_collector = metrics_collector
        self._processing_start_times: Dict[UUID, float] = {}
    
    def record_processing_start(self, summary_id: UUID) -> None:
        """
        Record start of summary processing.
        
        Args:
            summary_id: Summary ID being processed
        """
        self._processing_start_times[summary_id] = time.time()
        
        # Record counter for processing starts
        self._metrics_collector.record_counter(
            "summary_processing_started_total",
            labels={"summary_id": str(summary_id)}
        )
        
        logger.debug(
            "summary.metrics.processing_started",
            summary_id=str(summary_id)
        )
    
    def record_processing_success(
        self, 
        summary_id: UUID, 
        input_length: int, 
        output_length: int,
        provider: str
    ) -> None:
        """
        Record successful summary processing.
        
        Args:
            summary_id: Summary ID that was processed
            input_length: Length of input text
            output_length: Length of generated summary
            provider: Provider used for summarization
        """
        # Calculate processing duration
        start_time = self._processing_start_times.pop(summary_id, None)
        duration = time.time() - start_time if start_time else 0
        
        # Record success metrics
        self._metrics_collector.record_counter(
            "summary_processing_success_total",
            labels={"provider": provider}
        )
        
        self._metrics_collector.record_histogram(
            "summary_processing_duration_seconds",
            duration,
            labels={"provider": provider, "status": "success"}
        )
        
        self._metrics_collector.record_gauge(
            "summary_input_length_chars",
            input_length,
            labels={"provider": provider}
        )
        
        self._metrics_collector.record_gauge(
            "summary_output_length_chars",
            output_length,
            labels={"provider": provider}
        )
        
        # Calculate compression ratio
        compression_ratio = output_length / input_length if input_length > 0 else 0
        self._metrics_collector.record_gauge(
            "summary_compression_ratio",
            compression_ratio,
            labels={"provider": provider}
        )
        
        logger.info(
            "summary.metrics.processing_success",
            summary_id=str(summary_id),
            provider=provider,
            duration=duration,
            input_length=input_length,
            output_length=output_length,
            compression_ratio=compression_ratio
        )
    
    def record_processing_failure(self, summary_id: UUID, error: str) -> None:
        """
        Record failed summary processing.
        
        Args:
            summary_id: Summary ID that failed
            error: Error message
        """
        # Calculate processing duration
        start_time = self._processing_start_times.pop(summary_id, None)
        duration = time.time() - start_time if start_time else 0
        
        # Record failure metrics
        self._metrics_collector.record_counter(
            "summary_processing_failure_total",
            labels={"error_type": self._categorize_error(error)}
        )
        
        self._metrics_collector.record_histogram(
            "summary_processing_duration_seconds",
            duration,
            labels={"status": "failure", "error_type": self._categorize_error(error)}
        )
        
        logger.warning(
            "summary.metrics.processing_failure",
            summary_id=str(summary_id),
            error=error,
            duration=duration
        )
    
    def get_processing_stats(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """
        Get processing statistics.
        
        Args:
            provider: Optional provider filter
            
        Returns:
            Dict with processing statistics
        """
        # This would typically query stored metrics
        # For now, return basic stats structure
        stats = {
            "active_processing": len(self._processing_start_times),
            "provider_filter": provider,
            "timestamp": time.time()
        }
        
        if provider:
            stats["provider"] = provider
        
        logger.debug(
            "summary.metrics.stats_retrieved",
            stats=stats
        )
        
        return stats
    
    def _categorize_error(self, error: str) -> str:
        """
        Categorize error for metrics labeling.
        
        Args:
            error: Error message
            
        Returns:
            str: Error category
        """
        error_lower = error.lower()
        
        if "validation" in error_lower:
            return "validation_error"
        elif "timeout" in error_lower:
            return "timeout_error"
        elif "circuit" in error_lower:
            return "circuit_breaker_error"
        elif "api" in error_lower or "http" in error_lower:
            return "api_error"
        elif "provider" in error_lower:
            return "provider_error"
        else:
            return "unknown_error"