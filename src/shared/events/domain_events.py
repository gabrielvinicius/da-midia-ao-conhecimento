# src/shared/events/domain_events.py
from dataclasses import dataclass, asdict
from abc import ABC
from typing import Optional

from src.media_management.domain.media import MediaType


@dataclass(frozen=True)
class DomainEvent(ABC):
    """Base class for domain events."""
    def to_dict(self) -> dict:
        return asdict(self)

# --- Media Pipeline Events ---

@dataclass(frozen=True)
class MediaUploaded(DomainEvent):
    """A new media file has been uploaded and is ready for processing."""
    media_id: str
    user_id: str
    media_type: MediaType
    file_path: str
    storage_provider: str

@dataclass(frozen=True)
class AudioExtracted(DomainEvent):
    """Audio has been successfully extracted from a video file."""
    media_id: str
    audio_file_path: str
    storage_provider: str

@dataclass(frozen=True)
class TextContentReady(DomainEvent):
    """Text content has been generated from a media file (e.g., via transcription or PDF extraction)."""
    media_id: str
    text_content: str

# --- Transcription Events ---

@dataclass(frozen=True)
class TranscriptionRequested(DomainEvent):
    """A transcription is explicitly requested for a media item."""
    media_id: str
    provider: str

@dataclass(frozen=True)
class TranscriptionFailed(DomainEvent):
    media_id: str
    error: str

# --- Summarization Events ---

@dataclass(frozen=True)
class SummarizationRequested(DomainEvent):
    """A summary is explicitly requested for a media item."""
    media_id: str
    provider: str

@dataclass(frozen=True)
class SummarizationProgress(DomainEvent):
    """Reports the progress of a summarization task."""
    media_id: str
    progress: int
    stage: str
    estimated_total_seconds: Optional[float] = None
