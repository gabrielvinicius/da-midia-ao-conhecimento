# src/transcription/infrastructure/metrics.py
"""
Transcription metrics implementation - SRP compliance.
"""
from prometheus_client import Counter, Histogram, Gauge
from typing import Dict, Any

from src.transcription.domain.interfaces import TranscriptionMetrics


class PrometheusTranscriptionMetrics(TranscriptionMetrics):
    """
    Prometheus-based metrics implementation for transcription operations.
    Follows SRP - only responsible for metrics collection.
    """
    
    def __init__(self):
        # Operation counters
        self._operation_counter = Counter(
            'transcription_operations_total',
            'Total number of transcription operations',
            ['operation', 'provider', 'language', 'status']
        )
        
        # Operation duration histogram
        self._operation_duration = Histogram(
            'transcription_operation_duration_seconds',
            'Duration of transcription operations in seconds',
            ['operation', 'provider', 'language']
        )
        
        # Audio duration histogram
        self._audio_duration_histogram = Histogram(
            'transcription_audio_duration_seconds',
            'Duration of processed audio in seconds',
            ['provider', 'language']
        )
        
        # Real-time factor (RTF) histogram
        self._rtf_histogram = Histogram(
            'transcription_rtf',
            'Real-time factor (processing_time / audio_duration)',
            ['provider', 'language']
        )
        
        # Result length histogram
        self._result_length_histogram = Histogram(
            'transcription_result_length_chars',
            'Length of transcription result in characters',
            ['provider', 'language']
        )
        
        # Words per minute histogram
        self._wpm_histogram = Histogram(
            'transcription_words_per_minute',
            'Words per minute in transcribed audio',
            ['provider', 'language']
        )
        
        # Active transcriptions gauge
        self._active_transcriptions = Gauge(
            'transcription_active_operations',
            'Number of active transcription operations',
            ['provider']
        )
    
    async def record_operation(
        self, 
        operation: str, 
        provider: str,
        language: str,
        duration: float,
        success: bool,
        audio_duration: float,
        result_length: int
    ) -> None:
        """Record transcription operation metrics."""
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
        
        # Record audio and processing metrics (only for successful operations)
        if success and audio_duration > 0 and result_length > 0:
            self._audio_duration_histogram.labels(
                provider=provider,
                language=language
            ).observe(audio_duration)
            
            self._result_length_histogram.labels(
                provider=provider,
                language=language
            ).observe(result_length)
            
            # Calculate and record RTF
            rtf = duration / audio_duration if audio_duration > 0 else 0
            self._rtf_histogram.labels(
                provider=provider,
                language=language
            ).observe(rtf)
            
            # Estimate and record words per minute
            # Rough estimation: 1 character ≈ 0.2 words, so 5 chars = 1 word
            estimated_words = result_length / 5
            wpm = (estimated_words / audio_duration) * 60 if audio_duration > 0 else 0
            self._wpm_histogram.labels(
                provider=provider,
                language=language
            ).observe(wpm)


class InMemoryTranscriptionMetrics(TranscriptionMetrics):
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
        audio_duration: float,
        result_length: int
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
                "total_audio_duration": 0.0,
                "total_result_length": 0,
                "rtf_values": [],
                "wpm_values": []
            }
        
        metrics = self._metrics[key]
        metrics["total_operations"] += 1
        metrics["total_duration"] += duration
        metrics["min_duration"] = min(metrics["min_duration"], duration)
        metrics["max_duration"] = max(metrics["max_duration"], duration)
        
        if success:
            metrics["successful_operations"] += 1
            metrics["total_audio_duration"] += audio_duration
            metrics["total_result_length"] += result_length
            
            # Calculate RTF and WPM
            if audio_duration > 0:
                rtf = duration / audio_duration
                metrics["rtf_values"].append(rtf)
                
                estimated_words = result_length / 5
                wpm = (estimated_words / audio_duration) * 60
                metrics["wpm_values"].append(wpm)
        else:
            metrics["failed_operations"] += 1
    
    def get_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all recorded metrics (for testing)."""
        return self._metrics.copy()
    
    def reset_metrics(self) -> None:
        """Reset all metrics (for testing)."""
        self._metrics.clear()
    
    def get_average_rtf(self, operation: str, provider: str, language: str) -> float:
        """Get average real-time factor."""
        key = f"{operation}_{provider}_{language}"
        if key in self._metrics and self._metrics[key]["rtf_values"]:
            rtf_values = self._metrics[key]["rtf_values"]
            return sum(rtf_values) / len(rtf_values)
        return 0.0
    
    def get_average_wpm(self, operation: str, provider: str, language: str) -> float:
        """Get average words per minute."""
        key = f"{operation}_{provider}_{language}"
        if key in self._metrics and self._metrics[key]["wpm_values"]:
            wpm_values = self._metrics[key]["wpm_values"]
            return sum(wpm_values) / len(wpm_values)
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


class NoOpTranscriptionMetrics(TranscriptionMetrics):
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
        audio_duration: float,
        result_length: int
    ) -> None:
        """No-op implementation."""
        pass