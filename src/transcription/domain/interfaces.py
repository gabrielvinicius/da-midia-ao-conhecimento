"""
Domain interfaces for transcription module.
Follows Dependency Inversion Principle (DIP).
"""
from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID
from src.transcription.domain.transcription import Transcription
from src.media_management.domain.media import Media


class ITranscriptionRepository(ABC):
    """Interface for transcription repository operations."""
    
    @abstractmethod
    async def save(self, transcription: Transcription) -> Transcription:
        """Save or update a transcription."""
        pass
    
    @abstractmethod
    async def find_by_id(self, transcription_id: UUID) -> Optional[Transcription]:
        """Find transcription by ID."""
        pass
    
    @abstractmethod
    async def find_by_media_id(self, media_id: UUID) -> Optional[Transcription]:
        """Find transcription by media ID."""
        pass
    
    @abstractmethod
    async def delete(self, transcription_id: UUID) -> bool:
        """Delete a transcription."""
        pass


class ITranscriptionStateService(ABC):
    """Interface for transcription state management."""
    
    @abstractmethod
    async def start_processing(
        self, 
        media: Media, 
        language: str, 
        provider: str
    ) -> Transcription:
        """Start transcription processing."""
        pass
    
    @abstractmethod
    async def complete_processing(
        self, 
        media: Media, 
        transcription: Transcription, 
        text: str
    ) -> Transcription:
        """Complete transcription processing."""
        pass
    
    @abstractmethod
    async def fail_processing(self, media: Media, error: str) -> Transcription:
        """Mark transcription as failed."""
        pass


class ITranscriptionFileService(ABC):
    """Interface for transcription file operations."""
    
    @abstractmethod
    async def download_audio(self, file_path: str) -> bytes:
        """Download audio file for processing."""
        pass
    
    @abstractmethod
    async def extract_audio_from_video(self, video_path: str) -> str:
        """Extract audio from video file."""
        pass


class ISpeechRecognitionService(ABC):
    """Interface for speech recognition operations."""
    
    @abstractmethod
    async def transcribe(self, audio_bytes: bytes, language: str) -> str:
        """Transcribe audio to text."""
        pass
    
    @abstractmethod
    def get_supported_languages(self) -> list[str]:
        """Get list of supported languages."""
        pass


class ITranscriptionEventService(ABC):
    """Interface for transcription event publishing."""
    
    @abstractmethod
    async def publish_completion_event(self, media_id: UUID, text: str) -> None:
        """Publish transcription completion event."""
        pass
    
    @abstractmethod
    async def publish_failure_event(self, media_id: UUID, error: str) -> None:
        """Publish transcription failure event."""
        pass
    
    @abstractmethod
    async def publish_progress_event(self, media_id: UUID, progress: float) -> None:
        """Publish transcription progress event."""
        pass


class ITranscriptionMetricsService(ABC):
    """Interface for transcription metrics operations."""
    
    @abstractmethod
    def record_transcription_success(
        self, 
        media_id: UUID, 
        duration: float, 
        provider: str,
        language: str
    ) -> None:
        """Record successful transcription metrics."""
        pass
    
    @abstractmethod
    def record_transcription_failure(self, provider: str, error: str) -> None:
        """Record transcription failure metrics."""
        pass
    
    @abstractmethod
    def record_processing_duration(self, media_id: UUID, duration: float) -> None:
        """Record processing duration metrics."""
        pass