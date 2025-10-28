"""Upload metadata mapping collaborators for media command handlers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol


@dataclass(slots=True)
class UploadMetadata:
    """Normalized metadata produced after uploading a media file."""

    stored_path: str
    file_size: int


class UploadMetadataMapper(Protocol):
    """Maps raw storage metadata into normalized upload details."""

    def map(
        self,
        metadata: Optional[Dict[str, Any]],
        *,
        default_path: str,
        file_data: bytes,
    ) -> UploadMetadata:
        """Convert the raw metadata into normalized upload information."""


@dataclass(slots=True)
class DefaultUploadMetadataMapper(UploadMetadataMapper):
    """Default mapper that extracts the path and file size from metadata."""

    path_key: str = "file_path"
    size_key: str = "size"

    def map(
        self,
        metadata: Optional[Dict[str, Any]],
        *,
        default_path: str,
        file_data: bytes,
    ) -> UploadMetadata:
        if isinstance(metadata, dict):
            stored_path = str(metadata.get(self.path_key, default_path))
            if self.size_key in metadata:
                return UploadMetadata(stored_path=stored_path, file_size=int(metadata[self.size_key]))

        return UploadMetadata(stored_path=default_path, file_size=len(file_data))
