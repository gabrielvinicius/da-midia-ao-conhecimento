# src/shared/events/domain_events.py
from dataclasses import dataclass, asdict
from abc import ABC
from typing import Optional

from src.media_management.domain.media import MediaType


@dataclass(frozen=True)
class DomainEvent(ABC):
    """Base class for domain events."""
    def to_dict(self) -> dict:
        """Converts the event to a dictionary for serialization."""
        return asdict(self)


# --- Media Management Events ---

@dataclass(frozen=True)
class MediaUploaded(DomainEvent):
    """Event triggered when a new media file has been successfully uploaded."""
    media_id: str
    user_id: str
    media_type: MediaType
    file_path: str
    storage_provider: str

# --- Video Processing Events ---

@dataclass(frozen=True)
class AudioExtracted(DomainEvent):
    """Event triggered when audio has been successfully extracted from a video."""
    media_id: str
    audio_file_path: str
    storage_provider: str


# --- Transcription Events (Refactored to use media_id) ---

@dataclass(frozen=True)
class TranscriptionRequested(DomainEvent):
    """Event triggered when a transcription is explicitly requested."""
    media_id: str
    provider: str

@dataclass(frozen=True)
class TranscriptionStarted(DomainEvent):
    media_id: str

@dataclass(frozen=True)
class TranscriptionCompleted(DomainEvent):
    media_id: str
    transcription_id: str

@dataclass(frozen=True)
class TranscriptionFailed(DomainEvent):
    media_id: str
    error: str


# --- Summarization Events ---

@dataclass(frozen=True)
class SummarizationRequested(DomainEvent):
    """Event triggered when a user requests a new summary."""
    transcription_id: str
    provider: str


@dataclass(frozen=True)
class SummarizationProgress(DomainEvent):
    """Event to report the progress of a summarization task."""
    transcription_id: str
    progress: int
    stage: str
    estimated_total_seconds: Optional[float] = None
