from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from src.media_management.application.ports import (
    StorageUploaderPort,
    StorageUploadPort,
    UploadMetadata,
    UploadMetadataMapperPort,
    UploadResult,
)
from src.storage.infrastructure.dependencies import StorageServiceFactory


class StorageUploaderAdapter(StorageUploadPort):
    """Adapter wrapping StorageServiceFactory to FileStoragePort."""

    def __init__(
        self,
        factory: StorageServiceFactory,
        provider_name: str = "local",
    ) -> None:
        self._factory = factory
        self._provider = provider_name

    async def upload(
        self,
        *,
        file_data: bytes,
        destination: str,
        content_type: str,
    ) -> dict:
        storage = self._factory.create_storage_service(self._provider)
        return await storage.upload(
            file_data=file_data,
            destination=destination,
            content_type=content_type,
        )


class StorageServiceFactoryUploader(StorageUploaderPort):
    """Uploader que escolhe o provider dinamicamente a partir do command.

    Isto evita acoplamento a um provider fixo ("local") e garante que a seleção
    feita no upload (frontend/API) reflita o storage realmente utilizado.
    """

    def __init__(
        self,
        factory: StorageServiceFactory,
        *,
        default_provider: str = "local",
    ) -> None:
        self._factory = factory
        self._default_provider = default_provider

    async def upload(
        self,
        command,
        media_id: uuid.UUID,
        content_type: str,
    ) -> UploadResult:
        now = datetime.now(timezone.utc)
        safe_filename = os.path.basename(command.filename)
        destination_path = (
            f"{command.user_id}/{now.year}/{now.month:02d}/{media_id}/{safe_filename}"
        )

        provider = getattr(command, "storage_provider", None) or self._default_provider
        storage = self._factory.create_storage_service(str(provider))
        metadata = await storage.upload(
            file_data=command.file,
            destination=destination_path,
            content_type=content_type,
        )
        return UploadResult(destination_path=destination_path, metadata=metadata)


class DefaultUploadMetadataMapper(UploadMetadataMapperPort):
    """Standard implementation of metadata mapping."""

    def map(
        self,
        storage_metadata: Dict[str, Any],
        default_path: str,
        file_data: bytes,
    ) -> UploadMetadata:
        size = storage_metadata.get("size") or len(file_data)
        path = storage_metadata.get("path") or default_path
        return UploadMetadata(
            stored_path=path,
            file_size=size,
            hash_digest=storage_metadata.get("etag") or storage_metadata.get("hash"),
        )


class DefaultStorageUploader(StorageUploaderPort):
    """Standard implementation of storage uploading using the adapter."""

    def __init__(self, storage_adapter: StorageUploadPort):
        self.storage = storage_adapter

    async def upload(
        self,
        command,
        media_id: uuid.UUID,
        content_type: str,
    ) -> UploadResult:
        now = datetime.now(timezone.utc)
        safe_filename = os.path.basename(command.filename)
        destination_path = (
            f"{command.user_id}/{now.year}/{now.month:02d}/{media_id}/{safe_filename}"
        )

        metadata = await self.storage.upload(
            file_data=command.file,
            destination=destination_path,
            content_type=content_type,
        )
        return UploadResult(destination_path=destination_path, metadata=metadata)


__all__ = [
    "StorageUploaderAdapter",
    "StorageServiceFactoryUploader",
    "UploadResult",
    "UploadMetadata",
    "DefaultUploadMetadataMapper",
    "DefaultStorageUploader",
]
