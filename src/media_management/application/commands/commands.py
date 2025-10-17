"""
Media Management Commands - Pure data classes following Command Pattern
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from uuid import UUID


@dataclass(frozen=True)
class CreateMediaCommand:
    """Command to create new media"""
    user_id: str
    file: bytes
    filename: str
    storage_provider: str
    transcription_provider: Optional[str] = None
    summarization_provider: Optional[str] = None


@dataclass(frozen=True)
class DeleteMediaCommand:
    """Command to delete media"""
    media_id: UUID
    user_id: UUID
    force: bool = False


@dataclass(frozen=True)
class ReprocessMediaCommand:
    """Command to reprocess media"""
    media_id: UUID
    user_id: UUID
    processing_options: Optional[Dict[str, Any]] = None