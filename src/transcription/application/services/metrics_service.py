"""
Consolidated Transcription Metrics Service
Consolidates: TranscriptionMetricsService, TranscriptionMetricsServiceImpl
"""
import time
import structlog
from typing import Dict, Any, Optional
from uuid import UUID

from src.shared.monitoring.metrics_collector import MetricsCollector

logger = structlog.get_logger(__name__)


class TranscriptionMetricsService:
    """
    Consolidated service for all transcription metrics.
    Handles processing metrics, accuracy metrics, performance tracking.
    """
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self._processing_start_times: Dict[UUID, float] = {}

    # === PROCESSING METRICS ===
    
    def record_processing_start(self, transcription_id: UUID, media_type: str, provider: str) -> None:
        """Record start of transcription processing."""
        self._processing_start_times[transcription_id] = time.time()
        
        self.metrics_collector.record_counter(
            "transcription_processing_started_total",
            labels={"media_type": media_type, "provider": provider}
        )
        
        logger.info("transcription.processing.started", 
                   transcription_id=str(transcription_id), 
                   provider=provider)
    
    def record_processing_success(
        self, 
        transcription_id: UUID, 
        audio_size: int, 
        text_length: int,
        provider: str,
        language: str,
        confidence: Optional[float] = None
    ) -> None:
        """Record successful transcription processing."""
        start_time = self._processing_start_times.pop(transcription_id, None)
        duration = time.time() - start_time if start_time else 0
        
        # Record success metrics
        self.metrics_collector.record_counter(
            "transcription_processing_completed_total",
            labels={"status": "success", "provider": provider, "language": language}
        )
        
        self.metrics_collector.record_histogram(
            "transcription_processing_duration_seconds",
            duration,
            labels={"provider": provider, "language": language, "status": "success"}
        )
        
        # Audio and text metrics
        self.metrics_collector.record_gauge(
            "transcription_audio_size_bytes",
            audio_size,
            labels={"provider": provider}
        )
        
        self.metrics_collector.record_gauge(
            "transcription_text_length_chars",
            text_length,
            labels={"provider": provider, "language": language}
        )
        
        # Efficiency metrics
        if audio_size > 0:
            efficiency_ratio = text_length / audio_size
            self.metrics_collector.record_gauge(
                "transcription_efficiency_ratio",
                efficiency_ratio,
                labels={"provider": provider}
            )
        
        if duration > 0:
            processing_speed = audio_size / duration  # bytes per second
            self.metrics_collector.record_gauge(
                "transcription_processing_speed_bytes_per_second",
                processing_speed,
                labels={"provider": provider}
            )
        
        # Confidence metrics
        if confidence is not None:
            self.metrics_collector.record_histogram(
                "transcription_confidence_score",
                confidence,
                labels={"provider": provider, "language": language}
            )
        
        logger.info(
            "transcription.processing.completed",
            transcription_id=str(transcription_id),
            provider=provider,
            language=language,
            duration=duration,
            audio_size=audio_size,
            text_length=text_length,
            confidence=confidence
        )
    
    def record_processing_failure(self, transcription_id: UUID, error: str, provider: str, language: str) -> None:
        """Record failed transcription processing."""
        start_time = self._processing_start_times.pop(transcription_id, None)
        duration = time.time() - start_time if start_time else 0
        
        error_category = self._categorize_error(error)
        
        self.metrics_collector.record_counter(
            "transcription_processing_completed_total",
            labels={"status": "failure", "provider": provider, "language": language, "error_type": error_category}
        )
        
        self.metrics_collector.record_histogram(
            "transcription_processing_duration_seconds",
            duration,
            labels={"provider": provider, "language": language, "status": "failure"}
        )
        
        logger.error(
            "transcription.processing.failed",
            transcription_id=str(transcription_id),
            provider=provider,
            language=language,
            error=error,
            error_category=error_category,
            duration=duration
        )

    # === ACCURACY METRICS ===
    
    def record_speaker_diarization(self, transcription_id: UUID, speaker_count: int, provider: str) -> None:
        """Record speaker diarization metrics."""
        self.metrics_collector.record_gauge(
            "transcription_speaker_count",
            speaker_count,
            labels={"provider": provider}
        )
        
        self.metrics_collector.record_counter(
            "transcription_diarization_total",
            labels={"provider": provider}
        )
        
        logger.info("transcription.diarization.completed", 
                   transcription_id=str(transcription_id), 
                   speaker_count=speaker_count,
                   provider=provider)
    
    def record_language_detection(self, transcription_id: UUID, detected_language: str, confidence: float, provider: str) -> None:
        """Record language detection metrics."""
        self.metrics_collector.record_counter(
            "transcription_language_detection_total",
            labels={"detected_language": detected_language, "provider": provider}
        )
        
        self.metrics_collector.record_histogram(
            "transcription_language_detection_confidence",
            confidence,
            labels={"detected_language": detected_language, "provider": provider}
        )
        
        logger.info("transcription.language_detection.completed", 
                   transcription_id=str(transcription_id), 
                   detected_language=detected_language,
                   confidence=confidence,
                   provider=provider)

    # === QUALITY METRICS ===
    
    def record_transcription_quality(self, transcription_id: UUID, quality_score: float, provider: str, language: str) -> None:
        """Record transcription quality assessment."""
        self.metrics_collector.record_histogram(
            "transcription_quality_score",
            quality_score,
            labels={"provider": provider, "language": language}
        )
        
        # Categorize quality
        quality_category = self._categorize_quality(quality_score)
        self.metrics_collector.record_counter(
            "transcription_quality_category_total",
            labels={"category": quality_category, "provider": provider, "language": language}
        )
        
        logger.info("transcription.quality.assessed", 
                   transcription_id=str(transcription_id), 
                   quality_score=quality_score,
                   quality_category=quality_category,
                   provider=provider,
                   language=language)
    
    def record_word_error_rate(self, transcription_id: UUID, wer: float, provider: str, language: str) -> None:
        """Record word error rate."""
        self.metrics_collector.record_histogram(
            "transcription_word_error_rate",
            wer,
            labels={"provider": provider, "language": language}
        )
        
        logger.info("transcription.wer.calculated", 
                   transcription_id=str(transcription_id), 
                   wer=wer,
                   provider=provider,
                   language=language)

    # === PROVIDER METRICS ===
    
    def record_provider_performance(self, provider: str, success_rate: float, avg_duration: float) -> None:
        """Record provider performance metrics."""
        self.metrics_collector.record_gauge(
            "transcription_provider_success_rate",
            success_rate,
            labels={"provider": provider}
        )
        
        self.metrics_collector.record_gauge(
            "transcription_provider_avg_duration_seconds",
            avg_duration,
            labels={"provider": provider}
        )
        
        logger.info("transcription.provider.performance", 
                   provider=provider, 
                   success_rate=success_rate,
                   avg_duration=avg_duration)
    
    def record_provider_cost(self, provider: str, cost: float, duration_seconds: float) -> None:
        """Record provider cost metrics."""
        self.metrics_collector.record_gauge(
            "transcription_provider_cost_total",
            cost,
            labels={"provider": provider}
        )
        
        if duration_seconds > 0:
            cost_per_second = cost / duration_seconds
            self.metrics_collector.record_gauge(
                "transcription_provider_cost_per_second",
                cost_per_second,
                labels={"provider": provider}
            )

    # === PRIVATE METHODS ===
    
    def _categorize_error(self, error: str) -> str:
        """Categorize error for metrics labeling."""
        error_lower = error.lower()
        
        if "validation" in error_lower:
            return "validation_error"
        elif "timeout" in error_lower:
            return "timeout_error"
        elif "audio" in error_lower:
            return "audio_processing_error"
        elif "provider" in error_lower or "api" in error_lower:
            return "provider_error"
        elif "network" in error_lower or "connection" in error_lower:
            return "network_error"
        elif "language" in error_lower:
            return "language_error"
        elif "format" in error_lower:
            return "format_error"
        else:
            return "unknown_error"
    
    def _categorize_quality(self, quality_score: float) -> str:
        """Categorize quality score."""
        if quality_score >= 0.9:
            return "excellent"
        elif quality_score >= 0.8:
            return "good"
        elif quality_score >= 0.7:
            return "fair"
        elif quality_score >= 0.6:
            return "poor"
        else:
            return "very_poor"