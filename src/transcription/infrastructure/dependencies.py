# src/transcription/infrastructure/dependencies.py
"""
Dependency injection setup for transcription module - DIP compliance.
"""
import os
from typing import Optional

from src.transcription.domain.interfaces import (
    ITranscriptionRepository,
    SpeechRecognitionProviderFactory,
    TranscriptionOperationLogger,
    TranscriptionMetrics,
    TranscriptionNotificationService,
    TranscriptionStateManager,
    TranscriptionOrchestrator,
    AudioProcessor,
    TranscriptionValidator
)
from src.transcription.domain.services.transcription_coordinator import TranscriptionCoordinator
from src.transcription.application.services.transcription_state_manager import TranscriptionStateManagerImpl
from src.transcription.application.services.transcription_orchestrator import TranscriptionOrchestratorImpl
from src.transcription.application.services.audio_processor import DefaultAudioProcessor
from src.transcription.application.services.transcription_validator import DefaultTranscriptionValidator
from src.transcription.infrastructure.factory import get_speech_recognition_factory
from src.transcription.infrastructure.logging import StructuredTranscriptionLogger, NoOpTranscriptionLogger
from src.transcription.infrastructure.metrics import PrometheusTranscriptionMetrics, NoOpTranscriptionMetrics
from src.transcription.infrastructure.notification_service import (
    WebSocketTranscriptionNotificationService, 
    NoOpTranscriptionNotificationService
)
from src.transcription.infrastructure.providers.whisper_provider import WhisperConfiguration
from src.transcription.infrastructure.providers.fastwhisper_provider import FastWhisperConfiguration
from src.transcription.infrastructure.transcription_repository import TranscriptionRepository


class TranscriptionDependencyContainer:
    """
    Dependency injection container for transcription module.
    Follows DIP by managing dependencies through abstractions.
    """
    
    def __init__(self):
        self._factory: Optional[SpeechRecognitionProviderFactory] = None
        self._logger: Optional[TranscriptionOperationLogger] = None
        self._metrics: Optional[TranscriptionMetrics] = None
        self._notification_service: Optional[TranscriptionNotificationService] = None
        self._audio_processor: Optional[AudioProcessor] = None
        self._validator: Optional[TranscriptionValidator] = None
        self._orchestrator: Optional[TranscriptionOrchestrator] = None
    
    def get_speech_recognition_factory(self) -> SpeechRecognitionProviderFactory:
        """Get speech recognition provider factory."""
        if self._factory is None:
            self._factory = get_speech_recognition_factory()
        return self._factory
    
    def get_transcription_logger(self) -> TranscriptionOperationLogger:
        """Get transcription operation logger."""
        if self._logger is None:
            if os.getenv("ENABLE_TRANSCRIPTION_LOGGING", "true").lower() == "true":
                self._logger = StructuredTranscriptionLogger()
            else:
                self._logger = NoOpTranscriptionLogger()
        return self._logger
    
    def get_transcription_metrics(self) -> TranscriptionMetrics:
        """Get transcription metrics collector."""
        if self._metrics is None:
            if os.getenv("ENABLE_TRANSCRIPTION_METRICS", "true").lower() == "true":
                self._metrics = PrometheusTranscriptionMetrics()
            else:
                self._metrics = NoOpTranscriptionMetrics()
        return self._metrics
    
    def get_notification_service(self) -> TranscriptionNotificationService:
        """Get notification service."""
        if self._notification_service is None:
            # This would be injected from the notifications module
            # For now, use no-op for testing
            self._notification_service = NoOpTranscriptionNotificationService()
        return self._notification_service
    
    def get_audio_processor(self) -> AudioProcessor:
        """Get audio processor."""
        if self._audio_processor is None:
            target_sample_rate = int(os.getenv("TRANSCRIPTION_SAMPLE_RATE", "16000"))
            max_file_size = int(os.getenv("TRANSCRIPTION_MAX_FILE_SIZE", str(100 * 1024 * 1024)))
            min_duration = float(os.getenv("TRANSCRIPTION_MIN_DURATION", "0.1"))
            max_duration = float(os.getenv("TRANSCRIPTION_MAX_DURATION", "3600.0"))
            
            self._audio_processor = DefaultAudioProcessor(
                target_sample_rate=target_sample_rate,
                max_file_size=max_file_size,
                min_duration=min_duration,
                max_duration=max_duration
            )
        return self._audio_processor
    
    def get_transcription_validator(self) -> TranscriptionValidator:
        """Get transcription validator."""
        if self._validator is None:
            min_text_length = int(os.getenv("TRANSCRIPTION_MIN_TEXT_LENGTH", "1"))
            max_text_length = int(os.getenv("TRANSCRIPTION_MAX_TEXT_LENGTH", "1000000"))
            min_confidence = float(os.getenv("TRANSCRIPTION_MIN_CONFIDENCE", "0.0"))
            
            valid_languages = os.getenv("TRANSCRIPTION_VALID_LANGUAGES", "").split(",")
            valid_languages = [lang.strip() for lang in valid_languages if lang.strip()]
            
            self._validator = DefaultTranscriptionValidator(
                min_text_length=min_text_length,
                max_text_length=max_text_length,
                min_confidence=min_confidence,
                valid_languages=valid_languages if valid_languages else None
            )
        return self._validator
    
    def get_orchestrator(self, session) -> TranscriptionOrchestrator:
        """Get high-level transcription orchestrator."""
        if self._orchestrator is None:
            # Create repository
            repository = TranscriptionRepository(session)
            
            # Create provider
            provider_type = os.getenv("TRANSCRIPTION_PROVIDER", "whisper")
            provider = self._create_provider(provider_type)
            
            # Create coordinator
            coordinator = TranscriptionCoordinator(
                provider=provider,
                audio_processor=self.get_audio_processor(),
                validator=self.get_transcription_validator(),
                logger=self.get_transcription_logger(),
                metrics=self.get_transcription_metrics(),
                notification_service=self.get_notification_service()
            )
            
            # Create state manager
            state_manager = TranscriptionStateManagerImpl(repository)
            
            # Create orchestrator
            self._orchestrator = TranscriptionOrchestratorImpl(
                repository=repository,
                state_manager=state_manager,
                coordinator=coordinator
            )
        
        return self._orchestrator
    
    def _create_provider(self, provider_type: str):
        """Create speech recognition provider based on type."""
        factory = self.get_speech_recognition_factory()
        
        if provider_type == "whisper":
            config = WhisperConfiguration(
                model_name=os.getenv("WHISPER_MODEL", "base"),
                max_file_size=int(os.getenv("TRANSCRIPTION_MAX_FILE_SIZE", str(100 * 1024 * 1024))),
                sample_rate=int(os.getenv("TRANSCRIPTION_SAMPLE_RATE", "16000")),
                enable_word_timestamps=os.getenv("WHISPER_WORD_TIMESTAMPS", "false").lower() == "true",
                enable_speaker_detection=os.getenv("WHISPER_SPEAKER_DETECTION", "false").lower() == "true"
            )
        elif provider_type == "fastwhisper":
            config = FastWhisperConfiguration(
                model_size=os.getenv("FASTWHISPER_MODEL_SIZE", "base"),
                device=os.getenv("FASTWHISPER_DEVICE", "cpu"),
                compute_type=os.getenv("FASTWHISPER_COMPUTE_TYPE", "int8"),
                max_file_size=int(os.getenv("TRANSCRIPTION_MAX_FILE_SIZE", str(100 * 1024 * 1024))),
                sample_rate=int(os.getenv("TRANSCRIPTION_SAMPLE_RATE", "16000")),
                beam_size=int(os.getenv("FASTWHISPER_BEAM_SIZE", "5")),
                vad_filter=os.getenv("FASTWHISPER_VAD_FILTER", "true").lower() == "true",
                min_silence_duration_ms=int(os.getenv("FASTWHISPER_MIN_SILENCE_MS", "500"))
            )
        else:
            raise ValueError(f"Unknown transcription provider: {provider_type}")
        
        return factory.create_provider(provider_type, config)


# Global container instance
_container = TranscriptionDependencyContainer()


def get_transcription_orchestrator(session) -> TranscriptionOrchestrator:
    """Dependency provider for transcription orchestrator."""
    return _container.get_orchestrator(session)


def get_speech_recognition_factory_dep() -> SpeechRecognitionProviderFactory:
    """Dependency provider for speech recognition factory."""
    return _container.get_speech_recognition_factory()


def get_transcription_logger_dep() -> TranscriptionOperationLogger:
    """Dependency provider for transcription logger."""
    return _container.get_transcription_logger()


def get_transcription_metrics_dep() -> TranscriptionMetrics:
    """Dependency provider for transcription metrics."""
    return _container.get_transcription_metrics()


def get_audio_processor_dep() -> AudioProcessor:
    """Dependency provider for audio processor."""
    return _container.get_audio_processor()


def get_transcription_validator_dep() -> TranscriptionValidator:
    """Dependency provider for transcription validator."""
    return _container.get_transcription_validator()