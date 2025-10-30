"""
Storage Commands - Pure data classes following Command Pattern
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from uuid import UUID


@dataclass(frozen=True)
class StoreFileCommand:
    """Command to store file"""
    file_data: bytes
    file_path: str
    content_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class DeleteFileCommand:
    """Command to delete file"""
    file_path: str
    force: bool = False


@dataclass(frozen=True)
class MoveFileCommand:
    """Command to move file"""
    source_path: str
    destination_path: str
    overwrite: bool = False


@dataclass(frozen=True)
class ValidateFileCommand:
    """Command to validate file"""
    file_path: str
    expected_checksum: Optional[str] = None
