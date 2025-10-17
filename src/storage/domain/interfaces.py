"""
Domain interfaces for storage module.
Follows Dependency Inversion Principle (DIP).
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, BinaryIO
from uuid import UUID
from enum import Enum
from datetime import datetime
import io


class StorageProvider(Enum):
    """Available storage providers."""
    LOCAL = "local"
    S3 = "s3"
    AZURE_BLOB = "azure_blob"
    GOOGLE_CLOUD = "google_cloud"
    DROPBOX = "dropbox"
    FTP = "ftp"
    SFTP = "sftp"
    MINIO = "minio"


class StorageOperation(Enum):
    """Storage operations for access control and logging."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    LIST = "list"
    COPY = "copy"
    MOVE = "move"
    METADATA = "metadata"


class CompressionType(Enum):
    """Supported compression types."""
    NONE = "none"
    GZIP = "gzip"
    ZIP = "zip"
    BZIP2 = "bzip2"
    LZMA = "lzma"


class EncryptionType(Enum):
    """Supported encryption types."""
    NONE = "none"
    AES256 = "aes256"
    AES128 = "aes128"
    SERVER_SIDE = "server_side"


class IStorageService(ABC):
    """Interface for storage service operations."""
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the name of the storage provider."""
        pass
    
    @abstractmethod
    def get_supported_operations(self) -> List[StorageOperation]:
        """Get list of supported operations."""
        pass
    
    @abstractmethod
    async def upload(
        self,
        file_content: Union[bytes, BinaryIO],
        file_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Upload file to storage.
        
        Args:
            file_content: File content as bytes or file-like object
            file_path: Path where to store the file
            metadata: Optional metadata to store with file
            
        Returns:
            Dictionary with upload result information
        """
        pass
    
    @abstractmethod
    async def download(self, file_path: str) -> bytes:
        """
        Download file from storage.
        
        Args:
            file_path: Path of the file to download
            
        Returns:
            File content as bytes
        """
        pass
    
    @abstractmethod
    async def delete(self, file_path: str) -> bool:
        """
        Delete file from storage.
        
        Args:
            file_path: Path of the file to delete
            
        Returns:
            True if deletion was successful
        """
        pass
    
    @abstractmethod
    async def exists(self, file_path: str) -> bool:
        """
        Check if file exists in storage.
        
        Args:
            file_path: Path of the file to check
            
        Returns:
            True if file exists
        """
        pass
    
    @abstractmethod
    async def get_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Get file metadata.
        
        Args:
            file_path: Path of the file
            
        Returns:
            Dictionary with file metadata
        """
        pass
    
    @abstractmethod
    async def list_files(
        self,
        prefix: str = "",
        limit: Optional[int] = None,
        recursive: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List files in storage.
        
        Args:
            prefix: Path prefix to filter files
            limit: Maximum number of files to return
            recursive: Whether to list files recursively
            
        Returns:
            List of file information dictionaries
        """
        pass
    
    @abstractmethod
    async def get_size(self, file_path: str) -> int:
        """
        Get file size.
        
        Args:
            file_path: Path of the file
            
        Returns:
            File size in bytes
        """
        pass
    
    @abstractmethod
    async def copy(self, source_path: str, destination_path: str) -> bool:
        """
        Copy file within storage.
        
        Args:
            source_path: Source file path
            destination_path: Destination file path
            
        Returns:
            True if copy was successful
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on storage service.
        
        Returns:
            Health check results
        """
        pass


class IStorageManager(ABC):
    """Interface for high-level storage management operations."""
    
    @abstractmethod
    async def store_file(
        self,
        file_content: Union[bytes, BinaryIO],
        filename: str,
        user_id: UUID,
        media_id: Optional[UUID] = None,
        provider: Optional[StorageProvider] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store file with automatic path generation and metadata.
        
        Args:
            file_content: File content
            filename: Original filename
            user_id: User ID for organizing files
            media_id: Optional media ID for association
            provider: Optional specific provider to use
            options: Additional storage options
            
        Returns:
            Generated file path
        """
        pass
    
    @abstractmethod
    async def retrieve_file(self, file_path: str, user_id: UUID) -> bytes:
        """
        Retrieve file with access control.
        
        Args:
            file_path: Path of file to retrieve
            user_id: User ID for access control
            
        Returns:
            File content
        """
        pass
    
    @abstractmethod
    async def delete_file(self, file_path: str, user_id: UUID) -> bool:
        """
        Delete file with access control.
        
        Args:
            file_path: Path of file to delete
            user_id: User ID for access control
            
        Returns:
            True if deletion successful
        """
        pass
    
    @abstractmethod
    async def get_file_info(self, file_path: str, user_id: UUID) -> Dict[str, Any]:
        """
        Get comprehensive file information.
        
        Args:
            file_path: Path of file
            user_id: User ID for access control
            
        Returns:
            File information dictionary
        """
        pass
    
    @abstractmethod
    async def list_user_files(
        self,
        user_id: UUID,
        prefix: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        List files for a specific user.
        
        Args:
            user_id: User ID
            prefix: Optional path prefix filter
            limit: Maximum files to return
            
        Returns:
            List of file information
        """
        pass


class IFileMetadataRepository(ABC):
    """Interface for file metadata repository operations."""
    
    @abstractmethod
    async def save_metadata(self, metadata) -> Any:
        """Save file metadata."""
        pass
    
    @abstractmethod
    async def find_by_path(self, file_path: str) -> Optional[Any]:
        """Find metadata by file path."""
        pass
    
    @abstractmethod
    async def find_by_media_id(self, media_id: UUID) -> Optional[Any]:
        """Find metadata by media ID."""
        pass
    
    @abstractmethod
    async def find_by_user_id(self, user_id: UUID) -> List[Any]:
        """Find metadata by user ID."""
        pass
    
    @abstractmethod
    async def update_metadata(self, file_path: str, updates: Dict[str, Any]) -> bool:
        """Update file metadata."""
        pass
    
    @abstractmethod
    async def delete_metadata(self, file_path: str) -> bool:
        """Delete file metadata."""
        pass


class IStorageAccessControl(ABC):
    """Interface for storage access control operations."""
    
    @abstractmethod
    async def can_access_file(
        self,
        user_id: UUID,
        file_path: str,
        operation: StorageOperation
    ) -> bool:
        """Check if user can perform operation on file."""
        pass
    
    @abstractmethod
    async def get_user_quota(self, user_id: UUID) -> Dict[str, Any]:
        """Get user storage quota information."""
        pass
    
    @abstractmethod
    async def check_quota_available(
        self,
        user_id: UUID,
        required_bytes: int
    ) -> bool:
        """Check if user has quota available for operation."""
        pass
    
    @abstractmethod
    async def update_quota_usage(
        self,
        user_id: UUID,
        bytes_delta: int
    ) -> None:
        """Update user quota usage."""
        pass


class IStoragePathGenerator(ABC):
    """Interface for storage path generation operations."""
    
    @abstractmethod
    def generate_file_path(
        self,
        user_id: UUID,
        filename: str,
        media_id: Optional[UUID] = None,
        prefix: Optional[str] = None
    ) -> str:
        """Generate organized file path."""
        pass
    
    @abstractmethod
    def generate_unique_filename(self, original_filename: str) -> str:
        """Generate unique filename to avoid conflicts."""
        pass
    
    @abstractmethod
    def extract_file_info(self, file_path: str) -> Dict[str, Any]:
        """Extract information from file path."""
        pass
    
    @abstractmethod
    def validate_path(self, file_path: str) -> bool:
        """Validate file path format."""
        pass


class IStorageEncryption(ABC):
    """Interface for storage encryption operations."""
    
    @abstractmethod
    async def encrypt_file(
        self,
        file_content: bytes,
        encryption_type: EncryptionType,
        key: Optional[str] = None
    ) -> bytes:
        """Encrypt file content."""
        pass
    
    @abstractmethod
    async def decrypt_file(
        self,
        encrypted_content: bytes,
        encryption_type: EncryptionType,
        key: Optional[str] = None
    ) -> bytes:
        """Decrypt file content."""
        pass
    
    @abstractmethod
    def generate_encryption_key(self, encryption_type: EncryptionType) -> str:
        """Generate encryption key."""
        pass


class IStorageCompression(ABC):
    """Interface for storage compression operations."""
    
    @abstractmethod
    async def compress_file(
        self,
        file_content: bytes,
        compression_type: CompressionType
    ) -> bytes:
        """Compress file content."""
        pass
    
    @abstractmethod
    async def decompress_file(
        self,
        compressed_content: bytes,
        compression_type: CompressionType
    ) -> bytes:
        """Decompress file content."""
        pass
    
    @abstractmethod
    def get_compression_ratio(
        self,
        original_size: int,
        compressed_size: int
    ) -> float:
        """Calculate compression ratio."""
        pass


class IStorageBackup(ABC):
    """Interface for storage backup operations."""
    
    @abstractmethod
    async def create_backup(
        self,
        file_path: str,
        backup_location: str
    ) -> str:
        """Create backup of file."""
        pass
    
    @abstractmethod
    async def restore_backup(
        self,
        backup_path: str,
        restore_location: str
    ) -> bool:
        """Restore file from backup."""
        pass
    
    @abstractmethod
    async def list_backups(self, file_path: str) -> List[Dict[str, Any]]:
        """List available backups for file."""
        pass
    
    @abstractmethod
    async def cleanup_old_backups(
        self,
        file_path: str,
        keep_count: int = 5
    ) -> int:
        """Clean up old backups, keeping specified count."""
        pass


class IStorageSync(ABC):
    """Interface for storage synchronization operations."""
    
    @abstractmethod
    async def sync_to_provider(
        self,
        source_provider: StorageProvider,
        target_provider: StorageProvider,
        file_path: str
    ) -> bool:
        """Sync file between storage providers."""
        pass
    
    @abstractmethod
    async def sync_folder(
        self,
        source_provider: StorageProvider,
        target_provider: StorageProvider,
        folder_path: str
    ) -> Dict[str, Any]:
        """Sync entire folder between providers."""
        pass
    
    @abstractmethod
    async def get_sync_status(self, file_path: str) -> Dict[str, Any]:
        """Get synchronization status of file."""
        pass


class IStorageMetrics(ABC):
    """Interface for storage metrics operations."""
    
    @abstractmethod
    async def track_operation(
        self,
        provider: StorageProvider,
        operation: StorageOperation,
        file_size: int,
        duration: float,
        success: bool
    ) -> None:
        """Track storage operation metrics."""
        pass
    
    @abstractmethod
    async def get_provider_metrics(
        self,
        provider: StorageProvider
    ) -> Dict[str, Any]:
        """Get metrics for storage provider."""
        pass
    
    @abstractmethod
    async def get_usage_statistics(
        self,
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Get storage usage statistics."""
        pass
    
    @abstractmethod
    async def get_performance_metrics(
        self,
        time_range: str = "24h"
    ) -> Dict[str, Any]:
        """Get storage performance metrics."""
        pass


class IStorageConfiguration(ABC):
    """Interface for storage configuration management."""
    
    @abstractmethod
    async def get_provider_config(self, provider: StorageProvider) -> Dict[str, Any]:
        """Get configuration for storage provider."""
        pass
    
    @abstractmethod
    async def update_provider_config(
        self,
        provider: StorageProvider,
        config: Dict[str, Any]
    ) -> bool:
        """Update provider configuration."""
        pass
    
    @abstractmethod
    async def validate_config(
        self,
        provider: StorageProvider,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate provider configuration."""
        pass
    
    @abstractmethod
    async def get_default_config(self, provider: StorageProvider) -> Dict[str, Any]:
        """Get default configuration for provider."""
        pass