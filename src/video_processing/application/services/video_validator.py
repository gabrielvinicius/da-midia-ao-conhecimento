"""
Video Validator Service - Single Responsibility: Validation operations.
Follows SRP by handling only validation concerns.
"""
import re
from typing import Dict, Any, Set
import structlog

from src.video_processing.domain.interfaces import IVideoValidator
from src.shared.exceptions.domain_exceptions import ValidationError

logger = structlog.get_logger(__name__)


class VideoValidator(IVideoValidator):
    """
    Validates video input and processing options following SRP.
    Single responsibility: All validation logic for video processing.
    """
    
    def __init__(
        self,
        min_video_size: int = 1024,  # 1KB minimum
        max_video_size: int = 500 * 1024 * 1024,  # 500MB maximum
        supported_formats: Set[str] = None
    ):
        self.min_video_size = min_video_size
        self.max_video_size = max_video_size
        self.supported_formats = supported_formats or {
            "mp4", "avi", "mov", "wmv", "flv", "webm", "mkv"
        }
    
    def validate_video_data(self, video_data: bytes) -> None:
        """
        Validate video data for processing.
        
        Args:
            video_data: Video data to validate
            
        Raises:
            ValidationError: If video data is invalid
        """
        if not video_data:
            raise ValidationError("Video data cannot be empty")
        
        if len(video_data) < self.min_video_size:
            raise ValidationError(
                f"Video file is too small for processing. "
                f"Minimum size: {self.min_video_size} bytes"
            )
        
        if len(video_data) > self.max_video_size:
            raise ValidationError(
                f"Video file is too large for processing. "
                f"Maximum size: {self.max_video_size} bytes"
            )
        
        # Basic video format validation (check for common video headers)
        if not self._is_valid_video_format(video_data):
            raise ValidationError(
                "Invalid video format. Supported formats: MP4, AVI, MOV, WMV, FLV, WebM, MKV"
            )
        
        logger.debug(
            "video.validation.data_validated",
            video_size=len(video_data)
        )
    
    def validate_format_support(self, format_name: str) -> None:
        """
        Validate if format is supported for conversion.
        
        Args:
            format_name: Format name to validate
            
        Raises:
            ValidationError: If format is not supported
        """
        if not format_name:
            raise ValidationError("Format name cannot be empty")
        
        if not isinstance(format_name, str):
            raise ValidationError("Format name must be a string")
        
        # Normalize format name
        normalized_format = format_name.lower().strip()
        
        if normalized_format not in self.supported_formats:
            raise ValidationError(
                f"Unsupported format: {format_name}. "
                f"Supported formats: {', '.join(sorted(self.supported_formats))}"
            )
        
        logger.debug(
            "video.validation.format_validated",
            format=normalized_format
        )
    
    def validate_processing_options(self, options: Dict[str, Any]) -> None:
        """
        Validate processing options.
        
        Args:
            options: Processing options to validate
            
        Raises:
            ValidationError: If options are invalid
        """
        if not isinstance(options, dict):
            raise ValidationError("Processing options must be a dictionary")
        
        # Validate resolution if provided
        if "resolution" in options:
            self._validate_resolution(options["resolution"])
        
        # Validate quality if provided
        if "quality" in options:
            self._validate_quality(options["quality"])
        
        # Validate bitrate if provided
        if "bitrate" in options:
            self._validate_bitrate(options["bitrate"])
        
        # Validate fps if provided
        if "fps" in options:
            self._validate_fps(options["fps"])
        
        logger.debug(
            "video.validation.options_validated",
            options=options
        )
    
    def _is_valid_video_format(self, video_data: bytes) -> bool:
        """
        Check if video data has valid format headers.
        
        Args:
            video_data: Video data to check
            
        Returns:
            bool: True if valid video format detected
        """
        if len(video_data) < 16:
            return False
        
        header = video_data[:16]
        
        # Check for common video format signatures
        # MP4 format
        if b'ftyp' in header[:12]:
            return True
        
        # AVI format
        if header[:4] == b'RIFF' and header[8:12] == b'AVI ':
            return True
        
        # MOV format (QuickTime)
        if b'moov' in header or b'mdat' in header:
            return True
        
        # WebM format
        if header[:4] == b'\x1a\x45\xdf\xa3':
            return True
        
        # MKV format
        if header[:4] == b'\x1a\x45\xdf\xa3':
            return True
        
        # FLV format
        if header[:3] == b'FLV':
            return True
        
        return False
    
    def _validate_resolution(self, resolution: Any) -> None:
        """Validate video resolution."""
        if not isinstance(resolution, dict):
            raise ValidationError("Resolution must be a dictionary with width and height")
        
        if "width" not in resolution or "height" not in resolution:
            raise ValidationError("Resolution must contain width and height")
        
        width = resolution["width"]
        height = resolution["height"]
        
        if not isinstance(width, int) or not isinstance(height, int):
            raise ValidationError("Resolution width and height must be integers")
        
        if width <= 0 or height <= 0:
            raise ValidationError("Resolution width and height must be positive")
        
        if width > 7680 or height > 4320:  # 8K limit
            raise ValidationError("Resolution exceeds maximum supported size (8K)")
    
    def _validate_quality(self, quality: Any) -> None:
        """Validate video quality setting."""
        if isinstance(quality, str):
            valid_qualities = {"low", "medium", "high", "ultra"}
            if quality.lower() not in valid_qualities:
                raise ValidationError(f"Invalid quality setting. Valid options: {valid_qualities}")
        elif isinstance(quality, (int, float)):
            if not (0 <= quality <= 100):
                raise ValidationError("Quality must be between 0 and 100")
        else:
            raise ValidationError("Quality must be a string or number")
    
    def _validate_bitrate(self, bitrate: Any) -> None:
        """Validate video bitrate."""
        if not isinstance(bitrate, (int, float)):
            raise ValidationError("Bitrate must be a number")
        
        if bitrate <= 0:
            raise ValidationError("Bitrate must be positive")
        
        if bitrate > 100_000_000:  # 100 Mbps limit
            raise ValidationError("Bitrate exceeds maximum supported rate (100 Mbps)")
    
    def _validate_fps(self, fps: Any) -> None:
        """Validate video frame rate."""
        if not isinstance(fps, (int, float)):
            raise ValidationError("FPS must be a number")
        
        if fps <= 0:
            raise ValidationError("FPS must be positive")
        
        if fps > 120:  # 120 fps limit
            raise ValidationError("FPS exceeds maximum supported rate (120 fps)")