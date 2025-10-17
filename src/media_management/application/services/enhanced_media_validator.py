"""
Enhanced Media Validator Service - Single Responsibility: Comprehensive validation.
Follows SRP by handling all validation concerns for media operations.
"""
import re
import mimetypes
from typing import Set, Dict, Any
from uuid import UUID
import structlog

from src.media_management.domain.interfaces import IEnhancedMediaValidator, MediaType
from src.shared.exceptions.domain_exceptions import ValidationError

logger = structlog.get_logger(__name__)


class EnhancedMediaValidator(IEnhancedMediaValidator):
    """
    Comprehensive media validator following SRP.
    Single responsibility: All validation logic for media operations.
    """
    
    def __init__(
        self,
        max_file_size: int = 100 * 1024 * 1024,  # 100MB
        min_file_size: int = 1024,  # 1KB
        supported_video_formats: Set[str] = None,
        supported_audio_formats: Set[str] = None,
        supported_image_formats: Set[str] = None
    ):
        self.max_file_size = max_file_size
        self.min_file_size = min_file_size
        
        self.supported_video_formats = supported_video_formats or {
            ".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm", ".mkv", ".m4v"
        }
        
        self.supported_audio_formats = supported_audio_formats or {
            ".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"
        }
        
        self.supported_image_formats = supported_image_formats or {
            ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff"
        }
        
        self.all_supported_formats = (
            self.supported_video_formats | 
            self.supported_audio_formats | 
            self.supported_image_formats
        )
    
    def validate_upload_request(self, file: bytes, filename: str, user_id: UUID) -> None:
        """
        Validate complete upload request.
        
        Args:
            file: File content bytes
            filename: Original filename
            user_id: User ID uploading the file
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate user ID
        if not user_id:
            raise ValidationError("User ID is required for upload")
        
        # Validate filename
        self._validate_filename(filename)
        
        # Validate file content
        self._validate_file_content(file)
        
        # Validate file size
        self._validate_file_size(file)
        
        # Validate file format
        self._validate_file_format(filename, file)
        
        # Validate media type consistency
        media_type = self._get_media_type(filename)
        self._validate_content_type_consistency(file, filename, media_type)
        
        logger.debug(
            "media.validation.upload_request_validated",
            filename=filename,
            file_size=len(file),
            user_id=str(user_id),
            media_type=media_type.value if media_type else None
        )
    
    def validate_media_metadata(self, metadata: dict) -> None:
        """
        Validate media metadata.
        
        Args:
            metadata: Media metadata dictionary
            
        Raises:
            ValidationError: If metadata is invalid
        """
        if not isinstance(metadata, dict):
            raise ValidationError("Metadata must be a dictionary")
        
        # Validate required metadata fields
        required_fields = ["filename", "content_type", "file_size"]
        for field in required_fields:
            if field not in metadata:
                raise ValidationError(f"Required metadata field missing: {field}")
        
        # Validate filename in metadata
        filename = metadata.get("filename")
        if not filename or not isinstance(filename, str):
            raise ValidationError("Invalid filename in metadata")
        
        self._validate_filename(filename)
        
        # Validate content type
        content_type = metadata.get("content_type")
        if not content_type or not isinstance(content_type, str):
            raise ValidationError("Invalid content type in metadata")
        
        # Validate file size
        file_size = metadata.get("file_size")
        if not isinstance(file_size, int) or file_size <= 0:
            raise ValidationError("Invalid file size in metadata")
        
        if file_size < self.min_file_size:
            raise ValidationError(f"File size too small: {file_size} bytes")
        
        if file_size > self.max_file_size:
            raise ValidationError(f"File size too large: {file_size} bytes")
        
        # Validate optional metadata
        if "duration" in metadata:
            duration = metadata["duration"]
            if not isinstance(duration, (int, float)) or duration < 0:
                raise ValidationError("Invalid duration in metadata")
        
        logger.debug(
            "media.validation.metadata_validated",
            metadata_fields=list(metadata.keys()),
            filename=filename,
            file_size=file_size
        )
    
    def validate_storage_configuration(self, provider: str, config: dict) -> None:
        """
        Validate storage provider configuration.
        
        Args:
            provider: Storage provider name
            config: Storage configuration dictionary
            
        Raises:
            ValidationError: If configuration is invalid
        """
        if not provider or not isinstance(provider, str):
            raise ValidationError("Storage provider name is required")
        
        if not config or not isinstance(config, dict):
            raise ValidationError("Storage configuration is required")
        
        # Validate provider-specific configurations
        if provider.lower() == "s3":
            self._validate_s3_configuration(config)
        elif provider.lower() == "local":
            self._validate_local_configuration(config)
        elif provider.lower() == "azure":
            self._validate_azure_configuration(config)
        else:
            # Generic validation for unknown providers
            required_fields = ["bucket_name", "region"]
            for field in required_fields:
                if field not in config:
                    logger.warning(
                        "media.validation.missing_config_field",
                        provider=provider,
                        field=field
                    )
        
        logger.debug(
            "media.validation.storage_config_validated",
            provider=provider,
            config_fields=list(config.keys())
        )
    
    def _validate_filename(self, filename: str) -> None:
        """Validate filename format and security."""
        if not filename or not filename.strip():
            raise ValidationError("Filename cannot be empty")
        
        # Check filename length
        if len(filename) > 255:
            raise ValidationError("Filename too long (max 255 characters)")
        
        # Check for dangerous characters
        dangerous_chars = ["<", ">", ":", '"', "|", "?", "*", "\0"]
        if any(char in filename for char in dangerous_chars):
            raise ValidationError("Filename contains invalid characters")
        
        # Check for path traversal attempts
        if ".." in filename or filename.startswith("/") or filename.startswith("\\"):
            raise ValidationError("Filename contains invalid path sequences")
        
        # Validate filename has extension
        if "." not in filename:
            raise ValidationError("Filename must have an extension")
        
        # Check file extension
        extension = filename.lower().split(".")[-1]
        if f".{extension}" not in self.all_supported_formats:
            raise ValidationError(
                f"Unsupported file format: .{extension}. "
                f"Supported formats: {', '.join(sorted(self.all_supported_formats))}"
            )
    
    def _validate_file_content(self, file: bytes) -> None:
        """Validate file content."""
        if not file:
            raise ValidationError("File content cannot be empty")
        
        if not isinstance(file, bytes):
            raise ValidationError("File content must be bytes")
    
    def _validate_file_size(self, file: bytes) -> None:
        """Validate file size constraints."""
        file_size = len(file)
        
        if file_size < self.min_file_size:
            raise ValidationError(
                f"File is too small. Minimum size: {self.min_file_size} bytes"
            )
        
        if file_size > self.max_file_size:
            raise ValidationError(
                f"File is too large. Maximum size: {self.max_file_size} bytes"
            )
    
    def _validate_file_format(self, filename: str, file: bytes) -> None:
        """Validate file format against content."""
        extension = filename.lower().split(".")[-1]
        
        # Basic magic number validation for common formats
        magic_numbers = {
            "mp4": [b"\x00\x00\x00\x18ftypmp4", b"\x00\x00\x00\x20ftypmp4"],
            "avi": [b"RIFF"],
            "wav": [b"RIFF"],
            "mp3": [b"ID3", b"\xff\xfb", b"\xff\xfa"],
            "png": [b"\x89PNG\r\n\x1a\n"],
            "jpg": [b"\xff\xd8\xff"],
            "jpeg": [b"\xff\xd8\xff"],
            "gif": [b"GIF87a", b"GIF89a"],
            "pdf": [b"%PDF"]
        }
        
        if extension in magic_numbers:
            file_header = file[:20]  # Check first 20 bytes
            expected_headers = magic_numbers[extension]
            
            if not any(file_header.startswith(header) for header in expected_headers):
                logger.warning(
                    "media.validation.format_mismatch",
                    filename=filename,
                    extension=extension,
                    file_header=file_header[:10].hex()
                )
    
    def _validate_content_type_consistency(self, file: bytes, filename: str, media_type: MediaType) -> None:
        """Validate content type consistency."""
        extension = filename.lower().split(".")[-1]
        
        # Check media type consistency
        if media_type == MediaType.VIDEO and f".{extension}" not in self.supported_video_formats:
            raise ValidationError(f"Video file has unsupported extension: .{extension}")
        
        if media_type == MediaType.AUDIO and f".{extension}" not in self.supported_audio_formats:
            raise ValidationError(f"Audio file has unsupported extension: .{extension}")
        
        if media_type == MediaType.IMAGE and f".{extension}" not in self.supported_image_formats:
            raise ValidationError(f"Image file has unsupported extension: .{extension}")
    
    def _get_media_type(self, filename: str) -> MediaType:
        """Get media type from filename."""
        extension = f".{filename.lower().split('.')[-1]}"
        
        if extension in self.supported_video_formats:
            return MediaType.VIDEO
        elif extension in self.supported_audio_formats:
            return MediaType.AUDIO
        elif extension in self.supported_image_formats:
            return MediaType.IMAGE
        else:
            raise ValidationError(f"Unsupported media type for extension: {extension}")
    
    def _validate_s3_configuration(self, config: dict) -> None:
        """Validate S3-specific configuration."""
        required_fields = ["bucket_name", "region"]
        for field in required_fields:
            if field not in config:
                raise ValidationError(f"S3 configuration missing required field: {field}")
        
        # Validate bucket name format
        bucket_name = config["bucket_name"]
        if not re.match(r'^[a-z0-9.-]{3,63}$', bucket_name):
            raise ValidationError("Invalid S3 bucket name format")
    
    def _validate_local_configuration(self, config: dict) -> None:
        """Validate local storage configuration."""
        required_fields = ["base_path"]
        for field in required_fields:
            if field not in config:
                raise ValidationError(f"Local storage configuration missing required field: {field}")
        
        # Validate base path
        base_path = config["base_path"]
        if not base_path or not isinstance(base_path, str):
            raise ValidationError("Invalid base path for local storage")
    
    def _validate_azure_configuration(self, config: dict) -> None:
        """Validate Azure storage configuration."""
        required_fields = ["container_name", "account_name"]
        for field in required_fields:
            if field not in config:
                raise ValidationError(f"Azure storage configuration missing required field: {field}")
        
        # Validate container name
        container_name = config["container_name"]
        if not re.match(r'^[a-z0-9-]{3,63}$', container_name):
            raise ValidationError("Invalid Azure container name format")