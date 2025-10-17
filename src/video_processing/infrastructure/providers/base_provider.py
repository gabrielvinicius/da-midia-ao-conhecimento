# src/video_processing/infrastructure/providers/base_provider.py
"""
Base implementation for video processors - Template Method pattern.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
import asyncio

from src.video_processing.domain.interfaces import VideoProcessor, VideoConfiguration


class VideoProcessorError(Exception):
    """Base exception for video processor errors."""
    pass


class BaseVideoProcessor(VideoProcessor):
    """
    Base video processor implementing common functionality.
    Follows Template Method pattern and OCP.
    """
    
    def __init__(self, config: VideoConfiguration):
        self._config = config
        self._validate_configuration()
        self._initialize_processor()
    
    def _validate_configuration(self) -> None:
        """Validate processor configuration."""
        if not self._config.validate_config():
            raise VideoProcessorError("Invalid video processing configuration")
    
    @abstractmethod
    def _initialize_processor(self) -> None:
        """Initialize processor-specific components."""
        pass
    
    async def validate_video(self, video_data: bytes) -> bool:
        """Template method for video validation."""
        try:
            # Pre-validation hook
            await self._pre_validate(video_data)
            
            # Basic validation
            if not self._basic_validation(video_data):
                return False
            
            # Specific validation (implemented by subclasses)
            if not await self._do_validate(video_data):
                return False
            
            # Post-validation hook
            await self._post_validate(video_data)
            
            return True
            
        except Exception as e:
            await self._handle_validation_error(video_data, e)
            return False
    
    async def extract_video_info(self, video_data: bytes) -> Dict[str, Any]:
        """Template method for extracting video information."""
        try:
            # Pre-extraction hook
            await self._pre_extract_info(video_data)
            
            # Extract basic info (implemented by subclasses)
            info = await self._do_extract_info(video_data)
            
            # Post-process info
            processed_info = await self._post_process_info(info)
            
            # Post-extraction hook
            await self._post_extract_info(video_data, processed_info)
            
            return processed_info
            
        except Exception as e:
            await self._handle_info_extraction_error(video_data, e)
            raise VideoProcessorError(f"Info extraction failed") from e
    
    async def extract_audio_from_video(self, video_data: bytes) -> bytes:
        """Template method for audio extraction."""
        try:
            # Pre-extraction hook
            await self._pre_extract_audio(video_data)
            
            # Validate video has audio
            if not await self._has_audio_stream(video_data):
                raise VideoProcessorError("Video does not contain audio stream")
            
            # Extract audio (implemented by subclasses)
            audio_data = await self._do_extract_audio(video_data)
            
            # Post-process audio
            processed_audio = await self._post_process_audio(audio_data)
            
            # Post-extraction hook
            await self._post_extract_audio(video_data, processed_audio)
            
            return processed_audio
            
        except Exception as e:
            await self._handle_audio_extraction_error(video_data, e)
            raise VideoProcessorError(f"Audio extraction failed") from e
    
    def _basic_validation(self, video_data: bytes) -> bool:
        """Basic video validation."""
        if not video_data:
            return False
        
        # Check file size
        max_size = self._config.get_max_file_size()
        if len(video_data) > max_size:
            return False
        
        # Check minimum size
        if len(video_data) < 1024:  # Less than 1KB
            return False
        
        return True
    
    # Abstract methods to be implemented by subclasses
    @abstractmethod
    async def _do_validate(self, video_data: bytes) -> bool:
        """Actual validation implementation."""
        pass
    
    @abstractmethod
    async def _do_extract_info(self, video_data: bytes) -> Dict[str, Any]:
        """Actual info extraction implementation."""
        pass
    
    @abstractmethod
    async def _do_extract_audio(self, video_data: bytes) -> bytes:
        """Actual audio extraction implementation."""
        pass
    
    @abstractmethod
    async def _has_audio_stream(self, video_data: bytes) -> bool:
        """Check if video has audio stream."""
        pass
    
    # Hook methods (can be overridden by subclasses)
    async def _pre_validate(self, video_data: bytes) -> None:
        """Hook called before validation."""
        pass
    
    async def _post_validate(self, video_data: bytes) -> None:
        """Hook called after successful validation."""
        pass
    
    async def _pre_extract_info(self, video_data: bytes) -> None:
        """Hook called before info extraction."""
        pass
    
    async def _post_extract_info(self, video_data: bytes, info: Dict[str, Any]) -> None:
        """Hook called after info extraction."""
        pass
    
    async def _pre_extract_audio(self, video_data: bytes) -> None:
        """Hook called before audio extraction."""
        pass
    
    async def _post_extract_audio(self, video_data: bytes, audio_data: bytes) -> None:
        """Hook called after audio extraction."""
        pass
    
    async def _post_process_info(self, info: Dict[str, Any]) -> Dict[str, Any]:
        """Post-process extracted information."""
        # Add common metadata
        processed_info = {
            **info,
            "processor": self.__class__.__name__,
            "extraction_timestamp": asyncio.get_event_loop().time()
        }
        
        return processed_info
    
    async def _post_process_audio(self, audio_data: bytes) -> bytes:
        """Post-process extracted audio."""
        # Default implementation: return as-is
        return audio_data
    
    async def _handle_validation_error(self, video_data: bytes, error: Exception) -> None:
        """Handle validation errors."""
        pass
    
    async def _handle_info_extraction_error(self, video_data: bytes, error: Exception) -> None:
        """Handle info extraction errors."""
        pass
    
    async def _handle_audio_extraction_error(self, video_data: bytes, error: Exception) -> None:
        """Handle audio extraction errors."""
        pass
    
    def _detect_video_format(self, video_data: bytes) -> str:
        """Detect video format from header."""
        if len(video_data) < 12:
            return "unknown"
        
        # Check for common video format headers
        if video_data[4:8] == b'ftyp':
            return "mp4"
        elif video_data[:4] == b'RIFF' and video_data[8:12] == b'AVI ':
            return "avi"
        elif video_data[:8] == b'\x1a\x45\xdf\xa3':
            return "mkv"
        elif video_data[:4] == b'\x00\x00\x00\x14':
            return "mov"
        else:
            return "unknown"