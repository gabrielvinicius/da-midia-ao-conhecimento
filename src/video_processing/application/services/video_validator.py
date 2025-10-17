# src/video_processing/application/services/video_validator.py
"""
Video Validation Service - Single Responsibility Principle
Extracted from BaseVideoProcessingTemplate God Class (549 lines)
Handles all video input validation logic
"""

import os
from typing import Dict, Any, List
from enum import Enum

from src.video_processing.domain.interfaces import VideoProcessingInput, VideoOperation, VideoFormat
from src.shared.infrastructure.logging_config import get_logger

logger = get_logger("video_validator")


class VideoValidator:
    """
    Video validation with Single Responsibility:
    Validate video inputs, formats, operations, and constraints
    """
    
    def __init__(self, max_size_mb: int = 500):
        self.max_size_mb = max_size_mb
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.supported_input_formats = [
            VideoFormat.MP4, VideoFormat.AVI, VideoFormat.MOV, 
            VideoFormat.MKV, VideoFormat.WEBM
        ]
        self.supported_operations = list(VideoOperation)
        
    async def validate_input(
        self, 
        input_data: VideoProcessingInput, 
        options: Dict[str, Any] = None
    ) -> tuple[bool, List[str]]:
        """
        Validate video processing input
        Returns: (is_valid, error_messages)
        """
        errors = []
        options = options or {}
        
        # Validate video data
        data_errors = await self._validate_video_data(input_data)
        errors.extend(data_errors)
        
        # Validate format support
        format_errors = await self._validate_format_support(input_data)
        errors.extend(format_errors)
        
        # Validate operation requirements
        operation_errors = await self._validate_operation_requirements(input_data)
        errors.extend(operation_errors)
        
        # Validate constraints
        constraint_errors = await self._validate_constraints(input_data, options)
        errors.extend(constraint_errors)
        
        is_valid = len(errors) == 0
        
        if is_valid:
            logger.info(f"Video input validation passed: {input_data.operation.value}")
        else:
            logger.warning(f"Video input validation failed: {len(errors)} errors")
            for error in errors:
                logger.warning(f"  - {error}")
        
        return is_valid, errors
    
    async def _validate_video_data(self, input_data: VideoProcessingInput) -> List[str]:
        """Validate video data content"""
        errors = []
        
        if not input_data.video_data:
            errors.append("Video data is missing")
            return errors
        
        if len(input_data.video_data) == 0:
            errors.append("Video data is empty")
            return errors
        
        # Check minimum size (at least 1KB)
        if len(input_data.video_data) < 1024:
            errors.append("Video data too small (minimum 1KB)")
        
        # Check maximum size
        if len(input_data.video_data) > self.max_size_bytes:
            errors.append(
                f"Video size {len(input_data.video_data)} bytes exceeds "
                f"limit {self.max_size_bytes} bytes ({self.max_size_mb}MB)"
            )
        
        return errors
    
    async def _validate_format_support(self, input_data: VideoProcessingInput) -> List[str]:
        """Validate format support"""
        errors = []
        
        # Check input format
        if input_data.input_format not in self.supported_input_formats:
            supported_names = [f.value for f in self.supported_input_formats]
            errors.append(
                f"Input format '{input_data.input_format.value}' not supported. "
                f"Supported formats: {', '.join(supported_names)}"
            )
        
        # Check output format if specified
        if hasattr(input_data, 'output_format') and input_data.output_format:
            if input_data.output_format not in self.supported_input_formats:
                supported_names = [f.value for f in self.supported_input_formats]
                errors.append(
                    f"Output format '{input_data.output_format.value}' not supported. "
                    f"Supported formats: {', '.join(supported_names)}"
                )
        
        return errors
    
    async def _validate_operation_requirements(self, input_data: VideoProcessingInput) -> List[str]:
        """Validate operation-specific requirements"""
        errors = []
        
        # Check if operation is supported
        if input_data.operation not in self.supported_operations:
            operation_names = [op.value for op in self.supported_operations]
            errors.append(
                f"Operation '{input_data.operation.value}' not supported. "
                f"Supported operations: {', '.join(operation_names)}"
            )
            return errors
        
        # Operation-specific validation
        if input_data.operation == VideoOperation.CONVERT_FORMAT:
            if not hasattr(input_data, 'output_format') or not input_data.output_format:
                errors.append("Output format required for format conversion")
        
        elif input_data.operation == VideoOperation.EXTRACT_AUDIO:
            if not hasattr(input_data, 'output_audio_format') or not input_data.output_audio_format:
                errors.append("Output audio format required for audio extraction")
        
        elif input_data.operation == VideoOperation.RESIZE:
            if not hasattr(input_data, 'target_width') or not input_data.target_width:
                errors.append("Target width required for video resize")
            if not hasattr(input_data, 'target_height') or not input_data.target_height:
                errors.append("Target height required for video resize")
        
        elif input_data.operation == VideoOperation.COMPRESS:
            if hasattr(input_data, 'quality_level'):
                if input_data.quality_level < 1 or input_data.quality_level > 100:
                    errors.append("Quality level must be between 1 and 100")
        
        return errors
    
    async def _validate_constraints(self, input_data: VideoProcessingInput, options: Dict[str, Any]) -> List[str]:
        """Validate additional constraints"""
        errors = []
        
        # Duration constraints
        max_duration = options.get('max_duration_seconds', 3600)  # 1 hour default
        if hasattr(input_data, 'estimated_duration') and input_data.estimated_duration:
            if input_data.estimated_duration > max_duration:
                errors.append(
                    f"Video duration {input_data.estimated_duration}s exceeds "
                    f"maximum {max_duration}s"
                )
        
        # Resolution constraints
        max_width = options.get('max_width', 3840)  # 4K width
        max_height = options.get('max_height', 2160)  # 4K height
        
        if hasattr(input_data, 'width') and input_data.width:
            if input_data.width > max_width:
                errors.append(f"Video width {input_data.width} exceeds maximum {max_width}")
        
        if hasattr(input_data, 'height') and input_data.height:
            if input_data.height > max_height:
                errors.append(f"Video height {input_data.height} exceeds maximum {max_height}")
        
        return errors


# Default instance
video_validator = VideoValidator()