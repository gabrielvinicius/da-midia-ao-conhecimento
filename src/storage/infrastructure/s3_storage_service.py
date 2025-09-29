# src/storage/infrastructure/s3_storage_service.py
import asyncio
import boto3
from botocore.exceptions import ClientError
from pathlib import Path
from typing import Union, Optional, Tuple

from src.storage.application.storage_service import StorageService, StorageException
from src.storage.infrastructure.dependencies import register_storage
from src.storage.config.settings import StorageSettings


@register_storage("s3")
class S3StorageService(StorageService):
    def __init__(self):
        self.settings = StorageSettings()
        self.client = boto3.client(
            "s3",
            aws_access_key_id=self.settings.access_key,
            aws_secret_access_key=self.settings.secret_key,
            endpoint_url=self.settings.endpoint_url,
        )
        try:
            self.client.head_bucket(Bucket=self.settings.bucket_name)
        except ClientError:
            self.client.create_bucket(Bucket=self.settings.bucket_name)

    @property
    def provider_name(self) -> str:
        return "s3"

    def _sync_upload(self, file_path: str, file: bytes) -> bool:
        self.client.put_object(Bucket=self.settings.bucket_name, Key=file_path, Body=file)
        return True

    async def upload(self, file_path: Union[str, Path], file: bytes) -> bool:
        try:
            return await asyncio.to_thread(self._sync_upload, str(file_path), file)
        except Exception as e:
            raise StorageException("Error uploading to S3", e)

    def _sync_download(self, file_path: str) -> Optional[Tuple[bytes, str]]:
        try:
            response = self.client.get_object(Bucket=self.settings.bucket_name, Key=file_path)
            content = response["Body"].read()
            filename = file_path.split('/')[-1]
            return content, filename
        except self.client.exceptions.NoSuchKey:
            return None

    async def download(self, file_path: Union[str, Path]) -> Optional[Tuple[bytes, str]]:
        try:
            return await asyncio.to_thread(self._sync_download, str(file_path))
        except Exception as e:
            raise StorageException("Error downloading from S3", e)

    def _sync_delete(self, file_path: str) -> bool:
        try:
            self.client.delete_object(Bucket=self.settings.bucket_name, Key=file_path)
            return True
        except self.client.exceptions.NoSuchKey:
            return False

    async def delete(self, file_path: Union[str, Path]) -> bool:
        try:
            return await asyncio.to_thread(self._sync_delete, str(file_path))
        except Exception as e:
            raise StorageException("Error deleting from S3", e)

    def _sync_exists(self, file_path: str) -> bool:
        try:
            self.client.head_object(Bucket=self.settings.bucket_name, Key=file_path)
            return True
        except ClientError:
            return False

    async def exists(self, file_path: Union[str, Path]) -> bool:
        try:
            return await asyncio.to_thread(self._sync_exists, str(file_path))
        except Exception as e:
            raise StorageException("Error checking existence in S3", e)
