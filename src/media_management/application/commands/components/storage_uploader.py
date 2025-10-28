"""Storage upload collaborators for media command handlers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol, TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:  # pragma: no cover
    from src.media_management.application.commands.create_media_command import (
        CreateMediaCommand,
    )

from .storage_resolver import StorageServiceResolver


@dataclass(slots=True)
class StorageUploadResult:
    """Represents the outcome of a storage upload operation."""

    destination_path: str
    metadata: Optional[Dict[str, Any]]


class StorageUploader(Protocol):
    """Uploads media content and returns metadata about the stored file."""

    async def upload(
        self,
        command: "CreateMediaCommand",
        media_id: UUID,
        content_type: str,
    ) -> StorageUploadResult:
        """Upload the media content returning the storage metadata."""


@dataclass
class DefaultStorageUploader(StorageUploader):
    """Default uploader that delegates to a resolved storage service."""

    storage_resolver: StorageServiceResolver

    async def upload(
        self,
        command: "CreateMediaCommand",
        media_id: UUID,
        content_type: str,
    ) -> StorageUploadResult:
        storage_service = self.storage_resolver.resolve(command.storage_provider)
        destination_path = f"media/{media_id}/{command.filename}"

        metadata = await storage_service.upload(
            destination_path=destination_path,
            content=command.file,
            filename=command.filename,
            content_type=content_type,
            metadata=command.metadata or {},
        )

        return StorageUploadResult(destination_path=destination_path, metadata=metadata)
