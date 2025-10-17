# src/media_management/application/services/media_validator.py
from src.media_management.domain.media import MediaType
from src.media_management.domain.interfaces import IMediaValidator
from .file_type_detector import FileTypeDetector
from .file_size_validator import FileSizeValidator


class MediaValidator(IMediaValidator):
    """
    Media validation service following SRP and composition over inheritance.
    
    Delegates specific validation responsibilities to specialized services.
    """
    
    def __init__(
        self, 
        file_type_detector: FileTypeDetector,
        file_size_validator: FileSizeValidator
    ):
        self.file_type_detector = file_type_detector
        self.file_size_validator = file_size_validator

    def validate_file_content(self, file: bytes, filename: str) -> None:
        """
        Validate complete file content and metadata.
        
        Args:
            file: File content as bytes
            filename: Name of the file
            
        Raises:
            ValueError: If validation fails
        """
        if not filename:
            raise ValueError("File must have a filename.")
        if not file:
            raise ValueError("File content is empty.")

        self.validate_file_type(filename)
        self.validate_file_size(file)

    def validate_file_type(self, filename: str) -> None:
        """
        Validate file type is supported.
        
        Args:
            filename: Name of the file
            
        Raises:
            ValueError: If file type is not supported
        """
        if not self.file_type_detector.is_supported_type(filename):
            ext = self.file_type_detector.get_file_extension(filename)
            raise ValueError(f"Unsupported file type: {ext}")

    def validate_file_size(self, file: bytes) -> None:
        """
        Validate file size constraints.
        
        Args:
            file: File content as bytes
            
        Raises:
            ValueError: If file size exceeds limits
        """
        self.file_size_validator.validate_size(file)

    def get_media_type(self, filename: str) -> MediaType:
        """
        Determine media type from filename.
        
        Args:
            filename: Name of the file
            
        Returns:
            MediaType: The detected media type
            
        Raises:
            ValueError: If media type cannot be determined
        """
        return self.file_type_detector.get_media_type(filename)
