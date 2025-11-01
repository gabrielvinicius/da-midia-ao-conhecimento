# src/storage/domain/services/file_validator.py
from abc import ABC, abstractmethod
from typing import List

from src.storage.domain.value_objects.file_path import FilePath
from src.storage.domain.value_objects.file_size import FileSize


class FileValidationError(Exception):
    """Domain exception for file validation errors."""
    pass


class FileValidator(ABC):
    """Domain service interface for file validation (ISP compliance)."""
    
    @abstractmethod
    def validate_path(self, file_path: FilePath) -> None:
        """Validate file path format and security."""
        pass
    
    @abstractmethod
    def validate_size(self, file_size: FileSize) -> None:
        """Validate file size constraints."""
        pass
    
    @abstractmethod
    def validate_content_type(self, content_type: str) -> None:
        """Validate allowed content types."""
        pass


class DefaultFileValidator(FileValidator):
    """Default implementation of file validation rules."""
    
    def __init__(self, max_size_mb: int = 100, allowed_extensions: List[str] = None):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.allowed_extensions = allowed_extensions or [
            '.jpg', '.jpeg', '.png', '.gif', '.pdf', '.doc', '.docx', 
            '.mp3', '.mp4', '.avi', '.mov', '.txt', '.csv'
        ]
    
    def validate_path(self, file_path: FilePath) -> None:
        """Validate file path security and format."""
        path_str = file_path.value
        
        # Security checks
        if '..' in path_str or path_str.startswith('/'):
            raise FileValidationError("Invalid file path: potential directory traversal")
        
        # Extension check
        extension = file_path.get_extension()
        if extension and extension not in self.allowed_extensions:
            raise FileValidationError(f"File extension {extension} not allowed")
    
    def validate_size(self, file_size: FileSize) -> None:
        """Validate file size constraints."""
        if file_size.bytes > self.max_size_bytes:
            max_mb = self.max_size_bytes / (1024 * 1024)
            raise FileValidationError(f"File size {file_size} exceeds maximum {max_mb}MB")
    
    def validate_content_type(self, content_type: str) -> None:
        """Validate allowed content types."""
        allowed_types = [
            'image/', 'application/pdf', 'text/', 'audio/', 'video/',
            'application/msword', 'application/vnd.openxmlformats'
        ]
        
        if not any(content_type.startswith(allowed) for allowed in allowed_types):
            raise FileValidationError(f"Content type {content_type} not allowed")
