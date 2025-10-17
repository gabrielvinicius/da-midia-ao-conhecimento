# src/storage/domain/entities/file_metadata.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from src.storage.domain.value_objects.file_path import FilePath
from src.storage.domain.value_objects.file_size import FileSize


@dataclass(frozen=True)
class FileMetadata:
    """Domain entity representing file metadata."""
    
    id: UUID
    file_path: FilePath
    size: FileSize
    content_type: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    checksum: Optional[str] = None
    
    def update_metadata(self, size: FileSize, checksum: Optional[str] = None) -> 'FileMetadata':
        """Create updated file metadata preserving immutability."""
        return FileMetadata(
            id=self.id,
            file_path=self.file_path,
            size=size,
            content_type=self.content_type,
            created_at=self.created_at,
            updated_at=datetime.utcnow(),
            checksum=checksum
        )