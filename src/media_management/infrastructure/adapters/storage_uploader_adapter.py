from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from src.media_management.application.ports import (
    StorageUploaderPort,
    UploadMetadata,
    UploadMetadataMapperPort,
    UploadResult,
)
from src.storage.application.ports import StorageServiceResolverPort  # Use Port


class StorageServiceFactoryUploader(StorageUploaderPort):
    """Uploader que escolhe o provider dinamicamente a partir do command."""

    def __init__(
        self,
        factory: StorageServiceResolverPort,  # Use Port
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

    async def discard(self, command, destination_path: str) -> None:
        provider = getattr(command, "storage_provider", None) or self._default_provider
        await self._factory.create_storage_service(str(provider)).delete(destination_path)


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


__all__ = [
    "StorageServiceFactoryUploader",
    "UploadResult",
    "UploadMetadata",
    "DefaultUploadMetadataMapper",
]