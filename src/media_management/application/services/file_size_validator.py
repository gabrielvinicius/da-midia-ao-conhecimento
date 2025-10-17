"""
File Size Validator - Single Responsibility: File size validation
Follows SRP by handling only file size validation logic.
"""
from src.media_management.config.settings import MediaSettings


class FileSizeValidator:
    """
    Service responsible ONLY for file size validation.
    
    Single Responsibility: File size constraints validation.
    """
    
    def __init__(self, settings: MediaSettings):
        self.settings = settings
    
    def validate_size(self, file: bytes) -> None:
        """
        Validate file size against configured limits.
        
        Args:
            file: File content as bytes
            
        Raises:
            ValueError: If file size exceeds limits
        """
        if len(file) > self.settings.max_file_size_bytes:
            raise ValueError(
                f"File too large. Max size is {self.settings.max_file_size_mb}MB, "
                f"got {len(file) / (1024 * 1024):.2f}MB"
            )
    
    def is_valid_size(self, file: bytes) -> bool:
        """
        Check if file size is within limits.
        
        Args:
            file: File content as bytes
            
        Returns:
            bool: True if file size is valid
        """
        return len(file) <= self.settings.max_file_size_bytes
    
    def get_file_size_mb(self, file: bytes) -> float:
        """
        Get file size in megabytes.
        
        Args:
            file: File content as bytes
            
        Returns:
            float: File size in MB
        """
        return len(file) / (1024 * 1024)