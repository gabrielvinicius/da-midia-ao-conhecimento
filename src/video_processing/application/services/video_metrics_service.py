"""
Video Metrics Service - Single Responsibility: Metrics collection and reporting.
Follows SRP by handling only metrics-related operations.
"""
import time
from typing import Dict, Any, Optional
import structlog

from src.video_processing.domain.interfaces import IVideoMetricsService
from src.shared.monitoring.metrics_collector import MetricsCollector

logger = structlog.get_logger(__name__)


class VideoMetricsService(IVideoMetricsService):
    """
    Handles video processing metrics following SRP.
    Single responsibility: Collect and report video processing metrics.
    """
    
    def __init__(self, metrics_collector: MetricsCollector):
        self._metrics_collector = metrics_collector
        self._processing_start_times: Dict[str, float] = {}
    
    def record_processing_start(self, media_id: str) -> None:
        """
        Record start of video processing.
        
        Args:
            media_id: Media ID being processed
        """
        self._processing_start_times[media_id] = time.time()
        
        # Record counter for processing starts
        self._metrics_collector.record_counter(
            "video_processing_started_total",
            labels={"media_id": media_id}
        )
        
        logger.debug(
            "video.metrics.processing_started",
            media_id=media_id
        )
    
    def record_processing_success(
        self, 
        media_id: str, 
        input_size: int, 
        output_size: int,
        format_conversion: str,
        duration: float
    ) -> None:
        """
        Record successful video processing.
        
        Args:
            media_id: Media ID that was processed
            input_size: Size of input video in bytes
            output_size: Size of output video in bytes
            format_conversion: Format conversion performed (e.g., "avi->mp4")
            duration: Processing duration in seconds
        """
        # Calculate processing duration if not provided
        if duration == 0:
            start_time = self._processing_start_times.pop(media_id, None)
            duration = time.time() - start_time if start_time else 0
        else:
            # Remove from tracking since duration was provided
            self._processing_start_times.pop(media_id, None)
        
        # Record success metrics
        self._metrics_collector.record_counter(
            "video_processing_success_total",
            labels={"format_conversion": format_conversion}
        )
        
        self._metrics_collector.record_histogram(
            "video_processing_duration_seconds",
            duration,
            labels={"format_conversion": format_conversion, "status": "success"}
        )
        
        self._metrics_collector.record_gauge(
            "video_input_size_bytes",
            input_size,
            labels={"format_conversion": format_conversion}
        )
        
        self._metrics_collector.record_gauge(
            "video_output_size_bytes",
            output_size,
            labels={"format_conversion": format_conversion}
        )
        
        # Calculate compression ratio
        compression_ratio = output_size / input_size if input_size > 0 else 0
        self._metrics_collector.record_gauge(
            "video_compression_ratio",
            compression_ratio,
            labels={"format_conversion": format_conversion}
        )
        
        # Calculate processing speed (MB/s)
        processing_speed = (input_size / (1024 * 1024)) / duration if duration > 0 else 0
        self._metrics_collector.record_gauge(
            "video_processing_speed_mbps",
            processing_speed,
            labels={"format_conversion": format_conversion}
        )
        
        logger.info(
            "video.metrics.processing_success",
            media_id=media_id,
            format_conversion=format_conversion,
            duration=duration,
            input_size=input_size,
            output_size=output_size,
            compression_ratio=compression_ratio,
            processing_speed_mbps=processing_speed
        )
    
    def record_processing_failure(self, media_id: str, error: str) -> None:
        """
        Record failed video processing.
        
        Args:
            media_id: Media ID that failed
            error: Error message
        """
        # Calculate processing duration
        start_time = self._processing_start_times.pop(media_id, None)
        duration = time.time() - start_time if start_time else 0
        
        error_category = self._categorize_error(error)
        
        # Record failure metrics
        self._metrics_collector.record_counter(
            "video_processing_failure_total",
            labels={"error_type": error_category}
        )
        
        self._metrics_collector.record_histogram(
            "video_processing_duration_seconds",
            duration,
            labels={"status": "failure", "error_type": error_category}
        )
        
        logger.warning(
            "video.metrics.processing_failure",
            media_id=media_id,
            error=error,
            error_category=error_category,
            duration=duration
        )
    
    def get_processing_stats(self, format_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        Get processing statistics.
        
        Args:
            format_filter: Optional format conversion filter
            
        Returns:
            Dict with processing statistics
        """
        stats = {
            "active_processing": len(self._processing_start_times),
            "format_filter": format_filter,
            "timestamp": time.time()
        }
        
        if format_filter:
            stats["format_conversion"] = format_filter
        
        logger.debug(
            "video.metrics.stats_retrieved",
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
        elif "format" in error_lower or "codec" in error_lower:
            return "format_error"
        elif "timeout" in error_lower:
            return "timeout_error"
        elif "memory" in error_lower or "space" in error_lower:
            return "resource_error"
        elif "ffmpeg" in error_lower:
            return "ffmpeg_error"
        elif "network" in error_lower or "connection" in error_lower:
            return "network_error"
        elif "permission" in error_lower or "access" in error_lower:
            return "permission_error"
        else:
            return "unknown_error"