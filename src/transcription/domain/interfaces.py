# src/transcription/domain/interfaces.py
"""
Domain interfaces for transcription module following DIP principle.
All high-level modules depend on these abstractions, not concrete implementations.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from src.transcription.domain.transcription import Transcription


class ISpeechRecognitionService(ABC):
    """Interface for core speech recognition operations."""
    
    @abstractmethod
    async def transcribe(
        self, 
        audio_bytes: bytes, 
        language: str = "en",
        transcription_id: Optional[UUID] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """Transcribe audio data."""
        pass
    
    @abstractmethod
    async def batch_transcribe(
        self, 
        audio_batches: Dict[UUID, bytes],
        language: str = "en",
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[UUID, str]:
        """Transcribe multiple audio files in batch."""
        pass


class ITranscriptionValidator(ABC):
    """Interface for transcription validation operations."""
    
    @abstractmethod
    def validate_audio_data(self, audio_data: bytes) -> None:
        """Validate audio data for transcription."""
        pass
    
    @abstractmethod
    def validate_language_code(self, language: str) -> None:
        """Validate language code is supported."""
        pass
    
    @abstractmethod
    def validate_transcription_quality(self, transcription: str, audio_data: bytes) -> None:
        """Validate transcription quality."""
        pass


class ITranscriptionMetricsService(ABC):
    """Interface for transcription metrics operations."""
    
    @abstractmethod
    def record_processing_start(self, transcription_id: UUID) -> None:
        """Record start of transcription processing."""
        pass
    
    @abstractmethod
    def record_processing_success(
        self, 
        transcription_id: UUID, 
        audio_size: int, 
        text_length: int,
        provider: str
    ) -> None:
        """Record successful transcription processing."""
        pass
    
    @abstractmethod
    def record_processing_failure(self, transcription_id: UUID, error: str) -> None:
        """Record failed transcription processing."""
        pass


class ITranscriptionStateManager(ABC):
    """Interface for transcription state management."""
    
    @abstractmethod
    async def update_status(
        self, 
        transcription_id: UUID, 
        status: str, 
        error_message: Optional[str] = None
    ) -> None:
        """Update transcription processing status."""
        pass
    
    @abstractmethod
    async def get_status(self, transcription_id: UUID) -> Optional[str]:
        """Get current transcription processing status."""
        pass


# Backward compatibility
SpeechRecognitionService = ISpeechRecognitionService


class IAudioProcessor(ABC):
    """Interface for audio processing services."""
    
    @abstractmethod
    async def process_audio(self, audio_data: bytes, target_format: str = "wav") -> bytes:
        """Process audio data to target format."""
        pass
    
    @abstractmethod
    async def extract_audio_from_video(self, video_data: bytes) -> bytes:
        """Extract audio track from video data."""
        pass


class INotificationService(ABC):
    """Interface for transcription notification services."""
    
    @abstractmethod
    async def notify_transcription_started(self, user_id: str, media_id: str):
        """Notify user that transcription has started."""
        pass
    
    @abstractmethod
    async def notify_transcription_completed(self, user_id: str, media_id: str, transcription: Transcription):
        """Notify user that transcription has completed."""
        pass
    
    @abstractmethod
    async def notify_transcription_failed(self, user_id: str, media_id: str, error: str):
        """Notify user that transcription has failed."""
        pass


class ITranscriptionOrchestrator(ABC):
    """Interface for transcription orchestration services."""
    
    @abstractmethod
    async def process_transcription(
        self,
        media_id: str,
        audio_data: bytes,
        language: str,
        provider: str,
        user_id: str
    ) -> Transcription:
        """Orchestrate audio transcription workflow."""
        pass
    
    @abstractmethod
    async def process_video_transcription(
        self,
        media_id: str,
        video_data: bytes,
        language: str,
        provider: str,
        user_id: str
    ) -> Transcription:
        """Orchestrate video transcription workflow."""
"""
Domain interfaces for transcription module following SOLID principles.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from enum import Enum

from src.transcription.domain.transcription import Transcription


class AudioFormat(str, Enum):
    """Supported audio formats."""
    MP3 = "mp3"
    WAV = "wav"
    M4A = "m4a"
    FLAC = "flac"
    OGG = "ogg"
    AAC = "aac"
    WMA = "wma"


class ITranscriptionReader(ABC):
    """Interface for read operations - ISP compliance."""
    
    @abstractmethod
    async def find_by_id(self, transcription_id: UUID) -> Optional[Transcription]:
        """Find transcription by ID."""
        pass
    
    @abstractmethod
    async def find_by_media_id(self, media_id: UUID) -> Optional[Transcription]:
        """Find transcription by media ID."""
        pass
    
    @abstractmethod
    async def exists_for_media(self, media_id: UUID) -> bool:
        """Check if transcription exists for media."""
        pass


class ITranscriptionWriter(ABC):
    """Interface for write operations - ISP compliance."""
    
    @abstractmethod
    async def save(self, transcription: Transcription) -> Transcription:
        """Save transcription."""
        pass
    
    @abstractmethod
    async def delete(self, transcription_id: UUID) -> bool:
        """Delete transcription."""
        pass


class ITranscriptionRepository(TranscriptionReader, TranscriptionWriter):
    """Complete repository interface combining read/write operations."""
    pass


class ISpeechRecognitionProvider(ABC):
    """Interface for speech recognition providers - ISP compliance."""
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identifier."""
        pass
    
    @abstractmethod
    async def transcribe(self, audio_data: bytes, language: str = "auto") -> Dict[str, Any]:
        """Transcribe audio to structured result."""
        pass
    
    @abstractmethod
    async def get_supported_languages(self) -> List[str]:
        """Get supported languages."""
        pass
    
    @abstractmethod
    async def get_capabilities(self) -> Dict[str, Any]:
        """Get provider capabilities."""
        pass


class IAudioProcessor(ABC):
    """Interface for audio processing - ISP compliance."""
    
    @abstractmethod
    async def validate_audio(self, audio_data: bytes) -> bool:
        """Validate audio data."""
        pass
    
    @abstractmethod
    async def extract_audio_info(self, audio_data: bytes) -> Dict[str, Any]:
        """Extract audio metadata."""
        pass
    
    @abstractmethod
    async def normalize_audio(self, audio_data: bytes) -> bytes:
        """Normalize audio for transcription."""
        pass
    
    @abstractmethod
    async def extract_audio_from_video(self, video_data: bytes) -> bytes:
        """Extract audio from video."""
        pass


class ITranscriptionValidator(ABC):
    """Interface for transcription validation - ISP compliance."""
    
    @abstractmethod
    async def validate_result(self, result: Dict[str, Any]) -> bool:
        """Validate transcription result."""
        pass
    
    @abstractmethod
    async def validate_language(self, language: str) -> bool:
        """Validate language code."""
        pass
    
    @abstractmethod
    async def get_result_quality_score(self, result: Dict[str, Any]) -> float:
        """Get quality score for transcription result."""
        pass


class ITranscriptionConfiguration(ABC):
    """Interface for transcription configuration - SRP compliance."""
    
    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """Get transcription configuration."""
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Validate configuration."""
        pass
    
    @abstractmethod
    def get_supported_formats(self) -> List[AudioFormat]:
        """Get supported audio formats."""
        pass
    
    @abstractmethod
    def get_max_file_size(self) -> int:
        """Get maximum file size in bytes."""
        pass


class ITranscriptionHealthCheck(ABC):
    """Interface for health checks - SRP compliance."""
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check transcription provider health."""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get transcription statistics."""
        pass


class ITranscriptionOperationLogger(ABC):
    """Interface for operation logging - SRP compliance."""
    
    @abstractmethod
    async def log_operation(
        self, 
        operation: str, 
        media_id: str,
        provider: str,
        language: str,
        success: bool,
        duration: float,
        audio_duration: Optional[float] = None,
        error: Optional[Exception] = None
    ) -> None:
        """Log transcription operation."""
        pass


class ITranscriptionMetrics(ABC):
    """Interface for metrics collection - SRP compliance."""
    
    @abstractmethod
    async def record_operation(
        self, 
        operation: str, 
        provider: str,
        language: str,
        duration: float,
        success: bool,
        audio_duration: float,
        result_length: int
    ) -> None:
        """Record transcription metrics."""
        pass


class ITranscriptionNotificationService(ABC):
    """Interface for notifications - SRP compliance."""
    
    @abstractmethod
    async def notify_started(self, media_id: str, user_id: str, language: str) -> None:
        """Notify transcription started."""
        pass
    
    @abstractmethod
    async def notify_progress(self, media_id: str, user_id: str, progress: float) -> None:
        """Notify transcription progress."""
        pass
    
    @abstractmethod
    async def notify_completed(
        self, 
        media_id: str, 
        user_id: str, 
        result: Dict[str, Any]
    ) -> None:
        """Notify transcription completed."""
        pass
    
    @abstractmethod
    async def notify_failed(
        self, 
        media_id: str, 
        user_id: str, 
        error: str
    ) -> None:
        """Notify transcription failed."""
        pass


class ITranscriptionStateManager(ABC):
    """Interface for state management - SRP compliance."""
    
    @abstractmethod
    async def start_processing(
        self, 
        media_id: str, 
        language: str, 
        provider: str
    ) -> Transcription:
        """Start processing and return transcription."""
        pass
    
    @abstractmethod
    async def complete_processing(
        self, 
        transcription: Transcription, 
        result: Dict[str, Any]
    ) -> Transcription:
        """Complete processing with result."""
        pass
    
    @abstractmethod
    async def fail_processing(
        self, 
        transcription: Transcription, 
        error: str
    ) -> Transcription:
        """Mark processing as failed."""
        pass
    
    @abstractmethod
    async def update_progress(
        self, 
        transcription: Transcription, 
        progress: float
    ) -> Transcription:
        """Update processing progress."""
        pass


class ISpeechRecognitionProviderFactory(ABC):
    """Factory interface for creating speech recognition providers - DIP compliance."""
    
    @abstractmethod
    def create_provider(
        self, 
        provider_type: str, 
        config: TranscriptionConfiguration
    ) -> SpeechRecognitionProvider:
        """Create speech recognition provider instance."""
        pass
    
    @abstractmethod
    def get_available_providers(self) -> List[str]:
        """Get list of available provider types."""
        pass


class ITranscriptionOrchestrator(ABC):
    """High-level orchestrator interface - DIP compliance."""
    
    @abstractmethod
    async def process_transcription(
        self, 
        media_id: str, 
        audio_data: bytes,
        language: str,
        provider: str,
        user_id: str
    ) -> Transcription:
        """Process complete transcription workflow."""
        pass
    
    @abstractmethod
    async def get_transcription(self, media_id: str) -> Optional[Transcription]:
        """Get existing transcription."""
        pass
    
    @abstractmethod
    async def retry_failed_transcription(
        self, 
        media_id: str, 
        audio_data: bytes,
        language: str,
        provider: str,
        user_id: str
    ) -> Transcription:
        """Retry failed transcription."""
        pass