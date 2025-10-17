# src/video_processing/application/services/video_metrics_collector.py
"""
Video Metrics Collection Service - Single Responsibility Principle
Extracted from BaseVideoProcessingTemplate God Class (549 lines)
Handles video processing metrics and quality assessment
"""

import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.video_processing.domain.interfaces import VideoProcessingInput, VideoOperation
from src.shared.infrastructure.logging_config import get_logger

logger = get_logger("video_metrics")


class VideoMetricsCollector:
    """
    Video metrics collection with Single Responsibility:
    Collect and analyze video processing metrics and quality scores
    """
    
    def __init__(self):
        self.processing_history: List[Dict[str, Any]] = []
        self.quality_thresholds = {
            "compression_efficiency_min": 0.1,  # Minimum 10% compression
            "compression_efficiency_max": 0.9,  # Maximum 90% compression
            "quality_score_min": 0.7,           # Minimum quality score 70%
            "psnr_min": 30.0,                   # Minimum PSNR value
            "processing_time_max": 300.0        # Maximum 5 minutes processing
        }
    
    def start_processing_metrics(self, input_data: VideoProcessingInput, options: Dict[str, Any]) -> str:
        """
        Start metrics collection for video processing
        Returns metrics session ID
        """
        session_id = f"metrics_{int(time.time())}_{hash(input_data.video_data) % 1000}"
        
        metrics_session = {
            "session_id": session_id,
            "operation": input_data.operation.value,
            "input_format": input_data.input_format.value,
            "input_size": len(input_data.video_data),
            "start_time": datetime.utcnow(),
            "start_timestamp": time.time(),
            "options": options.copy(),
            "status": "started"
        }
        
        self.processing_history.append(metrics_session)
        
        logger.info(f"Started video processing metrics: {session_id}")
        return session_id
    
    def record_processing_completed(
        self, 
        session_id: str, 
        result: Dict[str, Any], 
        input_data: VideoProcessingInput
    ) -> Dict[str, Any]:
        """
        Record completion metrics and assess quality
        Returns comprehensive metrics report
        """
        
        # Find the session
        session = self._find_session(session_id)
        if not session:
            logger.warning(f"Metrics session not found: {session_id}")
            return {}
        
        # Calculate processing metrics
        end_time = datetime.utcnow()
        end_timestamp = time.time()
        processing_duration = end_timestamp - session["start_timestamp"]
        
        # Update session with completion data
        session.update({
            "end_time": end_time,
            "end_timestamp": end_timestamp,
            "processing_duration": processing_duration,
            "status": "completed",
            "result": result.copy()
        })
        
        # Calculate performance metrics
        performance_metrics = self._calculate_performance_metrics(session, result, input_data)
        
        # Assess quality metrics
        quality_metrics = self._assess_quality_metrics(session, result, input_data)
        
        # Create comprehensive report
        metrics_report = {
            "session_id": session_id,
            "operation": session["operation"],
            "processing_duration": processing_duration,
            "performance": performance_metrics,
            "quality": quality_metrics,
            "overall_score": self._calculate_overall_score(performance_metrics, quality_metrics),
            "timestamp": end_time.isoformat()
        }
        
        session["metrics_report"] = metrics_report
        
        logger.info(f"Video processing metrics completed: {session_id}")
        logger.info(f"Processing time: {processing_duration:.2f}s")
        logger.info(f"Overall score: {metrics_report['overall_score']:.2f}")
        
        return metrics_report
    
    def record_processing_failed(self, session_id: str, error: str) -> Dict[str, Any]:
        """Record processing failure metrics"""
        
        session = self._find_session(session_id)
        if not session:
            return {}
        
        end_timestamp = time.time()
        processing_duration = end_timestamp - session["start_timestamp"]
        
        session.update({
            "end_time": datetime.utcnow(),
            "end_timestamp": end_timestamp,
            "processing_duration": processing_duration,
            "status": "failed",
            "error": error
        })
        
        failure_report = {
            "session_id": session_id,
            "operation": session["operation"],
            "processing_duration": processing_duration,
            "status": "failed",
            "error": error,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        session["failure_report"] = failure_report
        
        logger.error(f"Video processing failed: {session_id} - {error}")
        return failure_report
    
    def _calculate_performance_metrics(
        self, 
        session: Dict[str, Any], 
        result: Dict[str, Any], 
        input_data: VideoProcessingInput
    ) -> Dict[str, Any]:
        """Calculate performance-related metrics"""
        
        processing_duration = session["processing_duration"]
        input_size = session["input_size"]
        
        # Throughput metrics
        throughput_mbps = (input_size / (1024 * 1024)) / max(processing_duration, 0.001)
        
        # Efficiency metrics
        time_efficiency = self._assess_time_efficiency(processing_duration, session["operation"])
        
        # Resource utilization (mock - in production would track actual CPU/memory)
        resource_efficiency = 0.85  # Mock value
        
        return {
            "processing_duration": processing_duration,
            "throughput_mbps": throughput_mbps,
            "time_efficiency": time_efficiency,
            "resource_efficiency": resource_efficiency,
            "input_size_mb": input_size / (1024 * 1024),
            "meets_time_threshold": processing_duration <= self.quality_thresholds["processing_time_max"]
        }
    
    def _assess_quality_metrics(
        self, 
        session: Dict[str, Any], 
        result: Dict[str, Any], 
        input_data: VideoProcessingInput
    ) -> Dict[str, Any]:
        """Assess quality-related metrics"""
        
        operation = session["operation"]
        quality_metrics = {"operation": operation}
        
        if operation == "format_conversion":
            quality_metrics.update(self._assess_conversion_quality(result, input_data))
        
        elif operation == "compression":
            quality_metrics.update(self._assess_compression_quality(result, input_data))
        
        elif operation == "resize":
            quality_metrics.update(self._assess_resize_quality(result, input_data))
        
        elif operation == "audio_extraction":
            quality_metrics.update(self._assess_audio_extraction_quality(result, input_data))
        
        elif operation == "frame_extraction":
            quality_metrics.update(self._assess_frame_extraction_quality(result, input_data))
        
        else:
            quality_metrics["quality_score"] = 0.8  # Default quality score
        
        return quality_metrics
    
    def _assess_conversion_quality(self, result: Dict[str, Any], input_data: VideoProcessingInput) -> Dict[str, Any]:
        """Assess format conversion quality"""
        
        compression_ratio = result.get("compression_ratio", 1.0)
        output_size = result.get("output_size", len(input_data.video_data))
        
        # Quality assessment based on compression efficiency
        compression_efficiency = 1.0 - abs(compression_ratio - 0.7)  # Target ~70% of original size
        quality_score = min(0.95, max(0.6, compression_efficiency))
        
        return {
            "compression_ratio": compression_ratio,
            "compression_efficiency": compression_efficiency,
            "quality_score": quality_score,
            "output_size_mb": output_size / (1024 * 1024),
            "size_reduction_percent": (1 - compression_ratio) * 100
        }
    
    def _assess_compression_quality(self, result: Dict[str, Any], input_data: VideoProcessingInput) -> Dict[str, Any]:
        """Assess compression quality"""
        
        compression_ratio = result.get("compression_ratio", 1.0)
        quality_level = result.get("quality_level", 80)
        
        # Quality score based on compression efficiency and quality level
        compression_efficiency = compression_ratio
        quality_preservation = quality_level / 100.0
        quality_score = (compression_efficiency * 0.4) + (quality_preservation * 0.6)
        
        # Check against thresholds
        meets_compression_threshold = (
            compression_ratio >= self.quality_thresholds["compression_efficiency_min"] and
            compression_ratio <= self.quality_thresholds["compression_efficiency_max"]
        )
        
        return {
            "compression_ratio": compression_ratio,
            "compression_efficiency": compression_efficiency,
            "quality_level": quality_level,
            "quality_preservation": quality_preservation,
            "quality_score": quality_score,
            "meets_compression_threshold": meets_compression_threshold,
            "estimated_psnr": 35.0 + (quality_level - 50) * 0.3  # Mock PSNR calculation
        }
    
    def _assess_resize_quality(self, result: Dict[str, Any], input_data: VideoProcessingInput) -> Dict[str, Any]:
        """Assess video resize quality"""
        
        scale_factor = result.get("scale_factor", 1.0)
        original_dims = result.get("original_dimensions", {})
        new_dims = result.get("new_dimensions", {})
        
        # Quality assessment based on scale factor
        if scale_factor > 1:
            # Upscaling - quality depends on algorithm quality
            quality_score = 0.75  # Moderate quality for upscaling
        elif scale_factor < 0.25:
            # Heavy downscaling - may lose detail
            quality_score = 0.65
        else:
            # Reasonable downscaling
            quality_score = 0.85
        
        return {
            "scale_factor": scale_factor,
            "original_dimensions": original_dims,
            "new_dimensions": new_dims,
            "quality_score": quality_score,
            "resize_type": "upscale" if scale_factor > 1 else "downscale"
        }
    
    def _assess_audio_extraction_quality(self, result: Dict[str, Any], input_data: VideoProcessingInput) -> Dict[str, Any]:
        """Assess audio extraction quality"""
        
        bitrate = result.get("bitrate", 128000)
        duration = result.get("estimated_duration", 0)
        
        # Quality based on bitrate
        if bitrate >= 256000:
            quality_score = 0.95
        elif bitrate >= 192000:
            quality_score = 0.88
        elif bitrate >= 128000:
            quality_score = 0.80
        else:
            quality_score = 0.70
        
        return {
            "bitrate": bitrate,
            "estimated_duration": duration,
            "quality_score": quality_score,
            "bitrate_category": self._categorize_audio_bitrate(bitrate)
        }
    
    def _assess_frame_extraction_quality(self, result: Dict[str, Any], input_data: VideoProcessingInput) -> Dict[str, Any]:
        """Assess frame extraction quality"""
        
        frame_count = result.get("frame_count", 0)
        extraction_rate = result.get("extraction_rate", 1)
        
        # Quality based on frame count and extraction success
        if frame_count > 0:
            quality_score = min(0.95, 0.7 + (frame_count / 100.0))
        else:
            quality_score = 0.0
        
        return {
            "frame_count": frame_count,
            "extraction_rate": extraction_rate,
            "quality_score": quality_score,
            "extraction_success": frame_count > 0
        }
    
    def _calculate_overall_score(self, performance: Dict[str, Any], quality: Dict[str, Any]) -> float:
        """Calculate overall processing score"""
        
        # Weight: 40% performance, 60% quality
        performance_score = performance.get("time_efficiency", 0.5) * performance.get("resource_efficiency", 0.5)
        quality_score = quality.get("quality_score", 0.5)
        
        overall_score = (performance_score * 0.4) + (quality_score * 0.6)
        return round(overall_score, 3)
    
    def _assess_time_efficiency(self, duration: float, operation: str) -> float:
        """Assess time efficiency based on operation type"""
        
        # Expected processing times by operation (in seconds per MB)
        expected_times = {
            "format_conversion": 2.0,
            "compression": 3.0, 
            "resize": 1.5,
            "audio_extraction": 1.0,
            "frame_extraction": 2.5
        }
        
        expected_time_per_mb = expected_times.get(operation, 2.0)
        
        # Simple efficiency calculation (can be improved)
        if duration <= expected_time_per_mb:
            return 1.0
        elif duration <= expected_time_per_mb * 2:
            return 0.8
        elif duration <= expected_time_per_mb * 3:
            return 0.6
        else:
            return 0.4
    
    def _categorize_audio_bitrate(self, bitrate: int) -> str:
        """Categorize audio bitrate quality"""
        if bitrate >= 320000:
            return "high"
        elif bitrate >= 192000:
            return "medium-high"
        elif bitrate >= 128000:
            return "medium"
        elif bitrate >= 96000:
            return "medium-low"
        else:
            return "low"
    
    def _find_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Find metrics session by ID"""
        for session in self.processing_history:
            if session["session_id"] == session_id:
                return session
        return None
    
    def get_metrics_summary(self, limit: int = 10) -> Dict[str, Any]:
        """Get summary of recent processing metrics"""
        
        recent_sessions = self.processing_history[-limit:]
        completed_sessions = [s for s in recent_sessions if s["status"] == "completed"]
        failed_sessions = [s for s in recent_sessions if s["status"] == "failed"]
        
        if not recent_sessions:
            return {"message": "No processing history available"}
        
        # Calculate averages
        avg_duration = 0
        avg_score = 0
        
        if completed_sessions:
            avg_duration = sum(s["processing_duration"] for s in completed_sessions) / len(completed_sessions)
            avg_score = sum(s.get("metrics_report", {}).get("overall_score", 0) for s in completed_sessions) / len(completed_sessions)
        
        return {
            "total_sessions": len(recent_sessions),
            "completed_sessions": len(completed_sessions),
            "failed_sessions": len(failed_sessions),
            "success_rate": len(completed_sessions) / len(recent_sessions) if recent_sessions else 0,
            "average_processing_duration": avg_duration,
            "average_quality_score": avg_score,
            "operations_breakdown": self._get_operations_breakdown(recent_sessions)
        }
    
    def _get_operations_breakdown(self, sessions: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get breakdown of operations in sessions"""
        breakdown = {}
        for session in sessions:
            operation = session["operation"]
            breakdown[operation] = breakdown.get(operation, 0) + 1
        return breakdown


# Default instance
video_metrics_collector = VideoMetricsCollector()