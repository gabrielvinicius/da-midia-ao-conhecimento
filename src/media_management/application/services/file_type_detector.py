"""
File Type Detector - Single Responsibility: Determine file types
Follows SRP by handling only file type detection logic.
"""
import os
from src.media_management.domain.media import MediaType
from src.media_management.config.settings import MediaSettings


class FileTypeDetector:
    """
    Service responsible ONLY for detecting and classifying file types.
    
    Single Responsibility: File type detection and classification.
    """
    
    def __init__(self, settings: MediaSettings):
        self.settings = settings
    
    def get_media_type(self, filename: str) -> MediaType:
        """
        Determine media type from filename extension.
        
        Args:
            filename: Name of the file
            
        Returns:
            MediaType: The detected media type
            
        Raises:
            ValueError: If file type cannot be determined
        """
        _, ext = os.path.splitext(filename or "")
        ext = ext.lower()
        
        if ext in self.settings.video_extensions:
            return MediaType.VIDEO
        if ext in self.settings.audio_extensions:
            return MediaType.AUDIO
        if ext in self.settings.text_extensions:
            return MediaType.TEXT
            
        raise ValueError(f"Cannot determine media type for: {ext}")
    
    def is_supported_type(self, filename: str) -> bool:
        """
        Check if file type is supported.
        
        Args:
            filename: Name of the file
            
        Returns:
            bool: True if file type is supported
        """
        _, ext = os.path.splitext(filename or "")
        ext = ext.lower()
        
        return (
            ext in self.settings.video_extensions
            or ext in self.settings.audio_extensions
            or ext in self.settings.text_extensions
        )
    
    def get_file_extension(self, filename: str) -> str:
        """
        Get normalized file extension.
        
        Args:
            filename: Name of the file
            
        Returns:
            str: Normalized file extension (lowercase, with dot)
        """
        _, ext = os.path.splitext(filename or "")
        return ext.lower()