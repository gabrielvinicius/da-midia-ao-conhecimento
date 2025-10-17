"""
Storage Validator Service - Single Responsibility: Validation operations.
Follows SRP by handling only validation concerns for storage operations.
"""
import re
import os
from typing import Dict, Any, Set, Union
from pathlib import Path
import structlog

from src.storage.domain.interfaces import IStorageValidator
from src.shared.exceptions.domain_exceptions import ValidationError

logger = structlog.get_logger(__name__)


class StorageValidator(IStorageValidator):
    """
    Validates storage operations following SRP.
    Single responsibility: All validation logic for storage operations.
    """
    
    def __init__(
        self,
        max_file_size: int = 500 * 1024 * 1024,  # 500MB
        min_file_size: int = 1,  # 1 byte
        allowed_extensions: Set[str] = None,
        blocked_extensions: Set[str] = None,
        max_path_length: int = 260  # Windows limit
    ):
        self.max_file_size = max_file_size
        self.min_file_size = min_file_size
        self.max_path_length = max_path_length
        
        self.allowed_extensions = allowed_extensions or {
            # Media files
            ".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm", ".mkv",
            ".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a",
            ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff",
            # Document files
            ".pdf", ".txt", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
            # Archive files
            ".zip", ".rar", ".7z", ".tar", ".gz"
        }
        
        self.blocked_extensions = blocked_extensions or {
            # Executable files
            ".exe", ".bat", ".cmd", ".com", ".scr", ".msi",
            ".dll", ".sys", ".bin", ".app", ".deb", ".rpm",
            # Script files
            ".js", ".vbs", ".ps1", ".sh", ".py", ".rb", ".php",
            # System files
            ".ini", ".cfg", ".conf", ".reg"
        }
        
        # Dangerous file patterns
        self.dangerous_patterns = [
            r"\.\.[\\/]",  # Path traversal
            r"^[\\/]",     # Absolute paths
            r"[<>:\"|?*]", # Invalid filename characters
            r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\.|$)",  # Windows reserved names
        ]
    
    def validate_file_path(self, file_path: Union[str, Path]) -> None:
        """
        Validate file path for security and format.
        
        Args:
            file_path: File path to validate
            
        Raises:
            ValidationError: If file path is invalid
        """
        if not file_path:
            raise ValidationError("File path cannot be empty")
        
        path_str = str(file_path)
        
        # Check path length
        if len(path_str) > self.max_path_length:
            raise ValidationError(
                f"File path too long. Maximum length: {self.max_path_length} characters"
            )
        
        # Check for dangerous patterns
        for pattern in self.dangerous_patterns:
            if re.search(pattern, path_str, re.IGNORECASE):
                raise ValidationError(f"File path contains dangerous pattern: {pattern}")
        
        # Validate filename
        filename = Path(path_str).name
        if not filename:
            raise ValidationError("File path must include a filename")
        
        self._validate_filename(filename)
        
        # Check directory structure
        self._validate_directory_structure(path_str)
        
        logger.debug(
            "storage.validation.path_validated",
            file_path=path_str,
            filename=filename
        )
    
    def validate_file_content(self, file_content: bytes, file_path: str) -> None:
        """
        Validate file content and size.
        
        Args:
            file_content: File content bytes
            file_path: File path for context
            
        Raises:
            ValidationError: If file content is invalid
        """
        if not isinstance(file_content, bytes):
            raise ValidationError("File content must be bytes")
        
        # Validate file size
        file_size = len(file_content)
        
        if file_size < self.min_file_size:
            raise ValidationError(
                f"File is too small. Minimum size: {self.min_file_size} bytes"
            )
        
        if file_size > self.max_file_size:
            raise ValidationError(
                f"File is too large. Maximum size: {self.max_file_size} bytes "
                f"({self.max_file_size / (1024*1024):.1f}MB)"
            )
        
        # Validate file extension vs content
        self._validate_content_consistency(file_content, file_path)
        
        # Check for malicious content patterns
        self._check_malicious_content(file_content, file_path)
        
        logger.debug(
            "storage.validation.content_validated",
            file_path=file_path,
            file_size=file_size
        )
    
    def validate_storage_operation(self, operation: str, provider: str) -> None:
        """
        Validate storage operation is allowed.
        
        Args:
            operation: Operation type (upload, download, delete, etc.)
            provider: Storage provider name
            
        Raises:
            ValidationError: If operation is not allowed
        """
        valid_operations = {"upload", "download", "delete", "exists", "list", "copy", "move"}
        
        if operation not in valid_operations:
            raise ValidationError(
                f"Invalid storage operation: {operation}. "
                f"Valid operations: {', '.join(valid_operations)}"
            )
        
        valid_providers = {"local", "s3", "azure", "gcs"}
        
        if provider not in valid_providers:
            raise ValidationError(
                f"Invalid storage provider: {provider}. "
                f"Valid providers: {', '.join(valid_providers)}"
            )
        
        logger.debug(
            "storage.validation.operation_validated",
            operation=operation,
            provider=provider
        )
    
    def validate_provider_configuration(self, provider: str, config: Dict[str, Any]) -> None:
        """
        Validate storage provider configuration.
        
        Args:
            provider: Storage provider name
            config: Provider configuration
            
        Raises:
            ValidationError: If configuration is invalid
        """
        if not isinstance(config, dict):
            raise ValidationError("Provider configuration must be a dictionary")
        
        if provider == "s3":
            self._validate_s3_config(config)
        elif provider == "azure":
            self._validate_azure_config(config)
        elif provider == "local":
            self._validate_local_config(config)
        elif provider == "gcs":
            self._validate_gcs_config(config)
        else:
            logger.warning(
                "storage.validation.unknown_provider",
                provider=provider
            )
        
        logger.debug(
            "storage.validation.config_validated",
            provider=provider,
            config_keys=list(config.keys())
        )
    
    def _validate_filename(self, filename: str) -> None:
        """Validate filename format and security."""
        if not filename.strip():
            raise ValidationError("Filename cannot be empty")
        
        # Check for dangerous characters
        dangerous_chars = ["<", ">", ":", '"', "|", "?", "*", "\0"]
        if any(char in filename for char in dangerous_chars):
            raise ValidationError(f"Filename contains invalid characters: {dangerous_chars}")
        
        # Check for Windows reserved names
        name_without_ext = filename.split('.')[0].upper()
        reserved_names = {
            "CON", "PRN", "AUX", "NUL", 
            "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
            "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
        }
        
        if name_without_ext in reserved_names:
            raise ValidationError(f"Filename uses reserved name: {name_without_ext}")
        
        # Check file extension
        if "." in filename:
            extension = filename.lower().split(".")[-1]
            extension_with_dot = f".{extension}"
            
            if extension_with_dot in self.blocked_extensions:
                raise ValidationError(f"File extension not allowed: {extension_with_dot}")
            
            if self.allowed_extensions and extension_with_dot not in self.allowed_extensions:
                raise ValidationError(
                    f"File extension not in allowed list: {extension_with_dot}. "
                    f"Allowed: {', '.join(sorted(self.allowed_extensions))}"
                )
    
    def _validate_directory_structure(self, path_str: str) -> None:
        """Validate directory structure in path."""
        path = Path(path_str)
        
        # Check directory depth (prevent deeply nested structures)
        max_depth = 10
        if len(path.parts) > max_depth:
            raise ValidationError(f"Directory structure too deep. Maximum depth: {max_depth}")
        
        # Validate each directory name
        for part in path.parts[:-1]:  # Exclude filename
            if not part or part in [".", ".."]:
                raise ValidationError("Invalid directory name in path")
            
            if len(part) > 255:
                raise ValidationError("Directory name too long (max 255 characters)")
    
    def _validate_content_consistency(self, file_content: bytes, file_path: str) -> None:
        """Validate file content matches extension."""
        if len(file_content) < 20:
            return  # Too small to validate magic numbers
        
        filename = Path(file_path).name.lower()
        file_header = file_content[:20]
        
        # Common file signatures (magic numbers)
        signatures = {
            ".jpg": [b"\xff\xd8\xff"],
            ".jpeg": [b"\xff\xd8\xff"],
            ".png": [b"\x89PNG\r\n\x1a\n"],
            ".gif": [b"GIF87a", b"GIF89a"],
            ".pdf": [b"%PDF"],
            ".zip": [b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"],
            ".mp4": [b"\x00\x00\x00\x18ftypmp4", b"\x00\x00\x00\x20ftypmp4"],
            ".mp3": [b"ID3", b"\xff\xfb", b"\xff\xfa"],
            ".wav": [b"RIFF"],
        }
        
        for ext, expected_headers in signatures.items():
            if filename.endswith(ext):
                if not any(file_header.startswith(header) for header in expected_headers):
                    logger.warning(
                        "storage.validation.content_mismatch",
                        filename=filename,
                        extension=ext,
                        header=file_header[:10].hex()
                    )
                break
    
    def _check_malicious_content(self, file_content: bytes, file_path: str) -> None:
        """Check for potentially malicious content patterns."""
        # Check for embedded scripts or executables
        malicious_patterns = [
            b"<script",
            b"javascript:",
            b"data:text/html",
            b"<?php",
            b"#!/bin/sh",
            b"#!/bin/bash",
            b"MZ\x90\x00",  # Windows executable header
        ]
        
        content_lower = file_content[:1024].lower()  # Check first 1KB
        
        for pattern in malicious_patterns:
            if pattern in content_lower:
                logger.warning(
                    "storage.validation.malicious_pattern_detected",
                    file_path=file_path,
                    pattern=pattern.decode('utf-8', errors='ignore')
                )
                # Don't raise error, just log warning
    
    def _validate_s3_config(self, config: Dict[str, Any]) -> None:
        """Validate S3 configuration."""
        required_fields = ["bucket_name", "region"]
        for field in required_fields:
            if field not in config:
                raise ValidationError(f"S3 configuration missing required field: {field}")
        
        # Validate bucket name format
        bucket_name = config["bucket_name"]
        if not re.match(r'^[a-z0-9.-]{3,63}$', bucket_name):
            raise ValidationError("Invalid S3 bucket name format")
    
    def _validate_azure_config(self, config: Dict[str, Any]) -> None:
        """Validate Azure storage configuration."""
        required_fields = ["container_name", "account_name"]
        for field in required_fields:
            if field not in config:
                raise ValidationError(f"Azure configuration missing required field: {field}")
    
    def _validate_local_config(self, config: Dict[str, Any]) -> None:
        """Validate local storage configuration."""
        if "base_path" in config:
            base_path = config["base_path"]
            if not isinstance(base_path, str) or not base_path.strip():
                raise ValidationError("Invalid base_path for local storage")
    
    def _validate_gcs_config(self, config: Dict[str, Any]) -> None:
        """Validate Google Cloud Storage configuration."""
        required_fields = ["bucket_name", "project_id"]
        for field in required_fields:
            if field not in config:
                raise ValidationError(f"GCS configuration missing required field: {field}")