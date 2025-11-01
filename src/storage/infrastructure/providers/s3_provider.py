# src/storage/infrastructure/providers/s3_provider.py
"""
S3-compatible storage provider - OCP and SRP compliance.
"""
import asyncio
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Optional, AsyncIterator, Dict, Any
from datetime import datetime
from uuid import uuid4

from src.storage.domain.interfaces import StorageConfiguration
from src.storage.domain.entities.file_metadata import FileMetadata
from src.storage.domain.value_objects.file_path import FilePath
from src.storage.domain.value_objects.file_size import FileSize
from src.storage.infrastructure.providers.base_provider import BaseStorageProvider


class S3StorageConfiguration(StorageConfiguration):
    """Configuration for S3 storage - SRP compliance."""
    
    def __init__(
        self,
        bucket_name: str,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        region: str = "us-east-1"
    ):
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
    
    def get_config(self) -> Dict[str, Any]:
        """Get configuration dictionary."""
        return {
            "bucket_name": self.bucket_name,
            "endpoint_url": self.endpoint_url,
            "region": self.region,
            # Don't include credentials in config output
        }
    
    def validate_config(self) -> bool:
        """Validate configuration."""
        required_fields = [
            self.bucket_name, self.endpoint_url, 
            self.access_key, self.secret_key
        ]
        return all(field and field.strip() for field in required_fields)


class S3StorageProvider(BaseStorageProvider):
    """
    S3-compatible storage provider.
    Follows OCP - can be extended without modification.
    """
    
    def __init__(self, config: S3StorageConfiguration):
        super().__init__(config)
        self._config = config
        self._client = self._create_client()
        self._ensure_bucket_exists()
    
    @property
    def provider_name(self) -> str:
        """Provider identifier."""
        return "s3"
    
    def _create_client(self):
        """Create S3 client with configuration."""
        try:
            return boto3.client(
                "s3",
                aws_access_key_id=self._config.access_key,
                aws_secret_access_key=self._config.secret_key,
                endpoint_url=self._config.endpoint_url,
                region_name=self._config.region
            )
        except NoCredentialsError as e:
            raise StorageProviderError("Invalid S3 credentials") from e
    
    def _ensure_bucket_exists(self) -> None:
        """Ensure bucket exists, create if necessary."""
        try:
            self._client.head_bucket(Bucket=self._config.bucket_name)
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                try:
                    self._client.create_bucket(Bucket=self._config.bucket_name)
                except ClientError as create_error:
                    raise StorageProviderError(
                        f"Failed to create bucket {self._config.bucket_name}"
                    ) from create_error
            else:
                raise StorageProviderError(
                    f"Failed to access bucket {self._config.bucket_name}"
                ) from e
    
    async def _do_write(self, file_path: FilePath, content: bytes) -> None:
        """Write file to S3."""
        await asyncio.to_thread(
            self._sync_write, 
            str(file_path), 
            content
        )
    
    def _sync_write(self, file_path: str, content: bytes) -> None:
        """Synchronous write operation."""
        self._client.put_object(
            Bucket=self._config.bucket_name,
            Key=file_path,
            Body=content
        )
    
    async def _do_read(self, file_path: FilePath) -> Optional[bytes]:
        """Read file from S3."""
        try:
            return await asyncio.to_thread(self._sync_read, str(file_path))
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            raise
    
    def _sync_read(self, file_path: str) -> bytes:
        """Synchronous read operation."""
        response = self._client.get_object(
            Bucket=self._config.bucket_name,
            Key=file_path
        )
        return response['Body'].read()
    
    async def _do_delete(self, file_path: FilePath) -> bool:
        """Delete file from S3."""
        try:
            await asyncio.to_thread(self._sync_delete, str(file_path))
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return False
            raise
    
    def _sync_delete(self, file_path: str) -> None:
        """Synchronous delete operation."""
        self._client.delete_object(
            Bucket=self._config.bucket_name,
            Key=file_path
        )
    
    async def exists(self, file_path: FilePath) -> bool:
        """Check if file exists in S3."""
        try:
            await asyncio.to_thread(
                self._client.head_object,
                Bucket=self._config.bucket_name,
                Key=str(file_path)
            )
            return True
        except ClientError:
            return False
    
    async def get_metadata(self, file_path: FilePath) -> Optional[FileMetadata]:
        """Get file metadata from S3."""
        try:
            response = await asyncio.to_thread(
                self._client.head_object,
                Bucket=self._config.bucket_name,
                Key=str(file_path)
            )
            
            return FileMetadata(
                id=uuid4(),  # In real implementation, should be persisted
                file_path=file_path,
                size=FileSize(response['ContentLength']),
                content_type=response.get('ContentType', 'application/octet-stream'),
                created_at=response['LastModified']
            )
        except ClientError:
            return None
    
    async def list_files(self, prefix: Optional[str] = None) -> AsyncIterator[FilePath]:
        """List files in S3 with optional prefix filter."""
        try:
            objects = await asyncio.to_thread(
                self._sync_list_objects, 
                prefix
            )
            
            for obj in objects:
                yield FilePath.from_path(obj['Key'])
                
        except ClientError:
            return
    
    def _sync_list_objects(self, prefix: Optional[str]) -> list:
        """Synchronous object listing."""
        kwargs = {'Bucket': self._config.bucket_name}
        if prefix:
            kwargs['Prefix'] = prefix
        
        objects = []
        paginator = self._client.get_paginator('list_objects_v2')
        
        for page in paginator.paginate(**kwargs):
            if 'Contents' in page:
                objects.extend(page['Contents'])
        
        return objects
    
    async def _pre_write(self, file_path: FilePath, content: bytes) -> None:
        """Hook for pre-write operations."""
        # Could add encryption, compression, etc.
        pass
    
    async def _post_write(self, file_path: FilePath, metadata: FileMetadata) -> None:
        """Hook for post-write operations."""
        # Could add tagging, lifecycle rules, etc.
        pass
