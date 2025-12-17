from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from src.storage.domain.value_objects.file_path import FilePath
from src.storage.domain.value_objects.file_size import FileSize


@dataclass(frozen=True, slots=True)
class FileMetadata:
    """Immutable description of a stored file."""

    id: UUID
    file_path: FilePath
    size: FileSize
    content_type: Optional[str]
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "file_path": str(self.file_path),
            "size_bytes": int(self.size.bytes),
            "content_type": self.content_type,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
