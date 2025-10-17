# src/video_processing/application/services/simplified_video_template.py
"""
Simplified Video Processing Template - Replacement for 549-line God Class
Composes the broken-down components following Single Responsibility Principle
"""

from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

from src.video_processing.domain.interfaces import VideoProcessingInput, VideoOperation
from .video_validator import VideoValidator, video_validator
from .video_processor import VideoProcessor, video_processor  
from .video_metrics_collector import VideoMetricsCollector, video_metrics_collector
from src.shared.infrastructure.logging_config import get_logger
from src.shared.patterns.template_method import TemplateMethodBase

logger = get_logger("simplified_video_template")


class SimplifiedVideoProcessingTemplate(TemplateMethodBase[VideoProcessingInput, Dict[str, Any]]):
    """
    Simplified Video Processing Template following SOLID principles
    
    Replaces the original 549-line BaseVideoProcessingTemplate God Class with composition of focused components:
    - VideoValidator: Input validation and constraint checking
    - VideoProcessor: Core processing operations and file management
    - VideoMetricsCollector: Metrics collection and quality assessment
    
    This class provides the same template method pattern but with much better separation of concerns.
    """
    
    def __init__(self, provider_name: str, tool_version: str = None):
        super().__init__(f"{provider_name}VideoProcessingTemplate")
        self.provider_name = provider_name
        self.tool_version = tool_version or "default"
        
        # Compose focused components
        self.validator = video_validator
        self.processor = video_processor
        self.metrics = video_metrics_collector
        
        # State tracking
        self.current_session_id: Optional[str] = None
        self.metrics_session_id: Optional[str] = None
        
        logger.info(f"Initialized simplified video template: {provider_name}")
    
    # === Template Method Implementation ===
    
    async def _initialize(self, input_data: VideoProcessingInput, options: Dict[str, Any]) -> Any:
        """Initialize video processing session"""
        
        # Add provider metadata to processing result
        self.processing_result.add_metadata("provider", self.provider_name)
        self.processing_result.add_metadata("tool_version", self.tool_version)
        self.processing_result.add_metadata("operation", input_data.operation.value)
        self.processing_result.add_metadata("input_format", input_data.input_format.value)
        
        # Start metrics collection
        self.metrics_session_id = self.metrics.start_processing_metrics(input_data, options)
        
        # Initialize provider-specific resources
        await self._initialize_provider(input_data, options)
        
        return {
            "provider": self.provider_name,
            "tool_version": self.tool_version,
            "metrics_session": self.metrics_session_id
        }
    
    async def _validate(self, input_data: VideoProcessingInput, options: Dict[str, Any]) -> bool:
        """Validate video input using specialized validator"""
        
        try:
            is_valid, errors = await self.validator.validate_input(input_data, options)
            
            if not is_valid:
                for error in errors:
                    self.processing_result.add_error(error)
                
                logger.warning(f"Video validation failed: {len(errors)} errors")
                return False
            
            logger.info("Video validation passed")
            return True
            
        except Exception as e:
            error_msg = f"Validation error: {str(e)}"
            self.processing_result.add_error(error_msg)
            logger.error(error_msg)
            return False
    
    async def _process(self, input_data: VideoProcessingInput, options: Dict[str, Any]) -> Dict[str, Any]:
        """Process video using specialized processor"""
        
        try:
            # Use the processor component for actual processing
            async with VideoProcessor() as processor:
                self.current_session_id = processor.session_id
                result = await processor.process_video(input_data, options)
                
                # Record successful processing metrics
                if self.metrics_session_id:
                    metrics_report = self.metrics.record_processing_completed(
                        self.metrics_session_id, result, input_data
                    )
                    result["metrics"] = metrics_report
                
                logger.info(f"Video processing completed successfully: {input_data.operation.value}")
                return result
                
        except Exception as e:
            error_msg = f"Processing error: {str(e)}"
            
            # Record failure metrics
            if self.metrics_session_id:
                self.metrics.record_processing_failed(self.metrics_session_id, error_msg)
            
            logger.error(error_msg)
            raise
    
    async def _finalize(self, result: Dict[str, Any], input_data: VideoProcessingInput, options: Dict[str, Any]) -> Dict[str, Any]:
        """Finalize processing with additional metadata"""
        
        # Add final metadata
        result.update({
            "provider": self.provider_name,
            "tool_version": self.tool_version,
            "session_id": self.current_session_id,
            "validation_config": self.validator.get_validation_config()
        })
        
        # Add processing summary to metadata
        if "metrics" in result:
            self.processing_result.add_metadata("quality_score", result["metrics"].get("overall_score", 0))
            self.processing_result.add_metadata("processing_duration", result["metrics"].get("processing_duration", 0))
        
        logger.info(f"Video processing finalized: {self.provider_name}")
        return result
    
    # === Abstract methods that providers must implement ===
    
    @abstractmethod
    async def _initialize_provider(self, input_data: VideoProcessingInput, options: Dict[str, Any]) -> None:
        """Initialize provider-specific resources"""
        pass
    
    @abstractmethod
    async def _get_supported_input_formats(self) -> list:
        """Get list of supported input formats for this provider"""
        pass
    
    # === Convenience methods for common operations ===
    
    async def validate_only(self, input_data: VideoProcessingInput, options: Dict[str, Any] = None) -> tuple[bool, list]:
        """Validate input without processing"""
        options = options or {}
        return await self.validator.validate_input(input_data, options)
    
    def get_metrics_summary(self, limit: int = 10) -> Dict[str, Any]:
        """Get processing metrics summary"""
        return self.metrics.get_metrics_summary(limit)
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get provider information"""
        return {
            "provider_name": self.provider_name,
            "tool_version": self.tool_version,
            "template_name": self.name,
            "validator_config": self.validator.get_validation_config()
        }
    
    # === Component access for advanced usage ===
    
    def get_validator(self) -> VideoValidator:
        """Get the validator component"""
        return self.validator
    
    def get_processor(self) -> VideoProcessor:
        """Get the processor component"""  
        return self.processor
    
    def get_metrics_collector(self) -> VideoMetricsCollector:
        """Get the metrics collector component"""
        return self.metrics
    
    # === Legacy compatibility methods ===
    
    async def _create_working_directory(self) -> None:
        """Legacy method - now handled by processor"""
        logger.warning("_create_working_directory is deprecated - handled by VideoProcessor")
    
    async def _save_input_video(self, input_data: VideoProcessingInput) -> str:
        """Legacy method - now handled by processor"""
        logger.warning("_save_input_video is deprecated - handled by VideoProcessor")
        return ""
    
    async def _analyze_video_properties(self, video_file: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy method - now handled by processor"""
        logger.warning("_analyze_video_properties is deprecated - handled by VideoProcessor")
        return {}


class FFmpegVideoProcessingTemplate(SimplifiedVideoProcessingTemplate):
    """
    FFmpeg-specific video processing template
    Simplified version of the original implementation
    """
    
    def __init__(self):
        super().__init__("ffmpeg", "6.0")
    
    async def _initialize_provider(self, input_data: VideoProcessingInput, options: Dict[str, Any]) -> None:
        """Initialize FFmpeg-specific resources"""
        
        # Check FFmpeg availability (mock)
        # In production: verify ffmpeg installation and version
        logger.info("FFmpeg provider initialized")
        
        # Set FFmpeg-specific options
        options.setdefault("ffmpeg_threads", 4)
        options.setdefault("ffmpeg_preset", "medium")
    
    async def _get_supported_input_formats(self) -> list:
        """Get FFmpeg supported formats"""
        from src.video_processing.domain.interfaces import VideoFormat
        
        # FFmpeg supports most common formats
        return [
            VideoFormat.MP4,
            VideoFormat.AVI, 
            VideoFormat.MOV,
            VideoFormat.MKV,
            VideoFormat.WEBM,
            VideoFormat.FLV,
            VideoFormat.WMV
        ]


# Backward compatibility - alias for the original God Class name
BaseVideoProcessingTemplate = SimplifiedVideoProcessingTemplate

# Default instances
default_video_template = SimplifiedVideoProcessingTemplate("default")
ffmpeg_video_template = FFmpegVideoProcessingTemplate()