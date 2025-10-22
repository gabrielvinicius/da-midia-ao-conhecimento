# src/transcription/domain/interfaces.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from uuid import UUID

from src.transcription.domain.transcription import Transcription # Para referenciar a entidade Transcription

class ISpeechRecognizer(ABC):
    """Interface for speech recognition operations."""

    @abstractmethod
    async def transcribe(self, audio_data: bytes, language: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Transcribes audio data into text."""
        pass

class ITranscriptionRepository(ABC):
    """Interface for managing Transcription entities."""

    @abstractmethod
    async def get_by_id(self, transcription_id: UUID) -> Optional[Transcription]:
        """Retrieves a transcription by its ID."""
        pass

    @abstractmethod
    async def add(self, transcription: Transcription) -> None:
        """Adds a new transcription to the repository."""
        pass

    @abstractmethod
    async def update(self, transcription: Transcription) -> None:
        """Updates an existing transcription in the repository."""
        pass

    @abstractmethod
    async def get_by_media_id(self, media_id: UUID) -> Optional[Transcription]:
        """Retrieves a transcription by its associated media ID."""
        pass

class ITranscriptionTaskScheduler(ABC):
    """Interface for scheduling transcription tasks."""

    @abstractmethod
    async def schedule_transcription_task(self, media_id: str, file_path: str, storage_provider: str, transcription_provider: str, language: str) -> Any:
        """Schedules a transcription task."""
        pass

class TranscriptionOperationLogger(ABC):
    """Interface for logging transcription operations."""

    @abstractmethod
    async def log_operation(
        self,
        operation: str,
        media_id: str,
        provider: str,
        success: bool,
        duration: float,
        error: Optional[Exception] = None
    ) -> None:
        """Log transcription operation with structured data."""
        pass

class TranscriptionMetrics(ABC):
    """Interface for recording transcription metrics."""

    @abstractmethod
    async def record_operation(
        self,
        operation: str,
        provider: str,
        duration: float,
        success: bool,
        input_audio_length_seconds: float,
        output_text_length_chars: int
    ) -> None:
        """Record transcription operation metrics."""
        pass
