"""
Transcription Metrics Service Implementation - Single Responsibility: Metrics collection.
Follows SRP by handling only metrics-related operations.
"""
import time
from typing import Dict, Any, Optional
from uuid import UUID
import structlog

from src.transcription.domain.interfaces import ITranscriptionMetricsService
from src.shared.monitoring.metrics_collector import MetricsCollector

logger = structlog.get_logger(__name__)


class TranscriptionMetricsServiceImpl(ITranscriptionMetricsService):
    """
    Handles transcription processing metrics following SRP.
    Single responsibility: Collect and report transcription metrics.
    """
    
    def __init__(self, metrics_collector: MetricsCollector):
        self._metrics_collector = metrics_collector
        self._processing_start_times: Dict[UUID, float] = {}
    
    def record_processing_start(self, transcription_id: UUID) -> None:
        """Record start of transcription processing."""
        self._processing_start_times[transcription_id] = time.time()
        
        self._metrics_collector.record_counter(
            "transcription_processing_started_total",
            labels={"transcription_id": str(transcription_id)}
        )
        
        logger.debug(
            "transcription.metrics.processing_started",
            transcription_id=str(transcription_id)
        )
    
    def record_processing_success(
        self, 
        transcription_id: UUID, 
        audio_size: int, 
        text_length: int,
        provider: str
    ) -> None:
        """Record successful transcription processing."""
        start_time = self._processing_start_times.pop(transcription_id, None)
        duration = time.time() - start_time if start_time else 0
        
        # Record success metrics
        self._metrics_collector.record_counter(
            "transcription_processing_success_total",
            labels={"provider": provider}
        )
        
        self._metrics_collector.record_histogram(
            "transcription_processing_duration_seconds",
            duration,
            labels={"provider": provider, "status": "success"}
        )
        
        self._metrics_collector.record_gauge(
            "transcription_audio_size_bytes",
            audio_size,
            labels={"provider": provider}
        )
        
        self._metrics_collector.record_gauge(
            "transcription_text_length_chars",
            text_length,
            labels={"provider": provider}
        )
        
        # Calculate efficiency ratio (text length per audio size)
        efficiency_ratio = text_length / audio_size if audio_size > 0 else 0
        self._metrics_collector.record_gauge(
            "transcription_efficiency_ratio",
            efficiency_ratio,
            labels={"provider": provider}
        )
        
        logger.info(
            "transcription.metrics.processing_success",
            transcription_id=str(transcription_id),
            provider=provider,
            duration=duration,
            audio_size=audio_size,
            text_length=text_length,
            efficiency_ratio=efficiency_ratio
        )
    
    def record_processing_failure(self, transcription_id: UUID, error: str) -> None:
        """Record failed transcription processing."""
        start_time = self._processing_start_times.pop(transcription_id, None)
        duration = time.time() - start_time if start_time else 0
        
        error_category = self._categorize_error(error)
        
        self._metrics_collector.record_counter(
            "transcription_processing_failure_total",
            labels={"error_type": error_category}
        )
        
        self._metrics_collector.record_histogram(
            "transcription_processing_duration_seconds",
            duration,
            labels={"status": "failure", "error_type": error_category}
        )
        
        logger.warning(
            "transcription.metrics.processing_failure",
            transcription_id=str(transcription_id),
            error=error,
            error_category=error_category,
            duration=duration
        )
    
    def _categorize_error(self, error: str) -> str:
        """Categorize error for metrics labeling."""
        error_lower = error.lower()
        
        if "validation" in error_lower:
            return "validation_error"
        elif "timeout" in error_lower:
            return "timeout_error"
        elif "circuit" in error_lower:
            return "circuit_breaker_error"
        elif "audio" in error_lower:
            return "audio_processing_error"
        elif "provider" in error_lower:
            return "provider_error"
        elif "network" in error_lower or "connection" in error_lower:
            return "network_error"
        else:
            return "unknown_error"