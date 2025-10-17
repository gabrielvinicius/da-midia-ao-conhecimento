# src/transcription/bootstrap.py
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

# Infrastructure & Config
from src.transcription.infrastructure.transcription_repository import TranscriptionRepository

# Queries
from src.transcription.application.queries.transcription_queries import TranscriptionQueries

# Command Handlers
from src.transcription.application.commands.set_speaker_aliases_command_handler import SetSpeakerAliasesCommandHandler
from src.transcription.application.commands.process_transcription_command_handler import ProcessTranscriptionCommandHandler

# SRP Services (Factories, Processors, etc.)
from src.transcription.application.services.transcription_factory import TranscriptionFactory
from src.transcription.application.services.default_audio_processor import DefaultAudioProcessor
from src.transcription.application.services.transcription_processor import TranscriptionProcessor
from src.transcription.application.services.transcription_provider_factory import TranscriptionProviderFactory

# Specialized Services
from src.transcription.application.services.transcription_notification_service import TranscriptionNotificationService
from src.transcription.application.services.transcription_orchestration_service import TranscriptionOrchestrationService
from src.transcription.application.services.transcription_metrics_service import TranscriptionMetricsService

# Enhanced SOLID Services
from src.transcription.application.services.speech_recognition_service import SpeechRecognitionService
from src.transcription.application.services.transcription_validator import TranscriptionValidator
from src.transcription.application.services.transcription_metrics_service_impl import TranscriptionMetricsServiceImpl
from src.transcription.application.services.transcription_state_manager_impl import TranscriptionStateManagerImpl

# External Dependencies
from src.media_management.application.queries.media_queries import MediaQueries
from src.notifications.infrastructure.connection_manager import ConnectionManager
from src.shared.monitoring.metrics_collector import MetricsCollector
from src.shared.infrastructure.cache import CacheService
from src.storage.infrastructure.dependencies import StorageServiceFactory
from src.shared.events.event_bus import EventBus
from src.transcription.infrastructure.interfaces import ISpeechRecognition


def bootstrap_transcription_module(
    db_session: AsyncSession, 
    media_queries: MediaQueries, 
    connection_manager: ConnectionManager,
    metrics_collector: MetricsCollector,
    cache_service: CacheService,
    storage_service_factory: StorageServiceFactory,
    event_bus: EventBus,
    speech_recognition_provider: ISpeechRecognition,
) -> Dict[str, Any]:
    """Constructs and returns the services for the transcription module following SOLID principles."""
    
    # --- Infrastructure and Config ---
    transcription_repository = TranscriptionRepository(db=db_session)
    transcription_queries = TranscriptionQueries(transcription_repository=transcription_repository)
    
    # --- SRP Services for Transcription Creation ---
    transcription_factory = TranscriptionFactory()
    audio_processor = DefaultAudioProcessor()
    provider_factory = TranscriptionProviderFactory()
    
    transcription_processor = TranscriptionProcessor(
        audio_processor=audio_processor,
        transcription_factory=transcription_factory,
        transcription_repository=transcription_repository
    )
    
    # --- SOLID Services (Following SRP) ---
    transcription_validator = TranscriptionValidator(
        min_audio_size=1024,
        max_audio_size=100 * 1024 * 1024,
        supported_languages={"en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja", "ko"}
    )
    
    transcription_metrics_service_enhanced = TranscriptionMetricsServiceImpl(
        metrics_collector=metrics_collector
    )
    
    transcription_state_manager = TranscriptionStateManagerImpl(
        cache_service=cache_service
    )
    
    # Enhanced Speech Recognition Service (SOLID compliant)
    enhanced_speech_recognition_service = SpeechRecognitionService(
        speech_recognition_provider=speech_recognition_provider,
        validator=transcription_validator,
        metrics_service=transcription_metrics_service_enhanced,
        state_manager=transcription_state_manager
    )
    
    # --- Legacy Services ---
    notification_service = TranscriptionNotificationService(connection_manager=connection_manager)
    metrics_service = TranscriptionMetricsService(metrics_provider=None)  # Legacy
    
    orchestration_service = TranscriptionOrchestrationService(
        transcription_processor=transcription_processor,
        provider_factory=provider_factory,
        metrics_service=metrics_service,
        notification_service=notification_service
    )
    
    # --- Command Handlers ---
    set_speaker_aliases_handler = SetSpeakerAliasesCommandHandler(
        transcription_repository=transcription_repository,
        media_queries=media_queries,
        connection_manager=connection_manager
    )
    
    process_transcription_handler = ProcessTranscriptionCommandHandler(
        orchestrator=orchestration_service,
        media_queries=media_queries,
        storage_service_factory=storage_service_factory,
        event_bus=event_bus
    )

    return {
        # Infrastructure
        "transcription_repository": transcription_repository,
        "transcription_queries": transcription_queries,
        
        # SOLID Services
        "transcription_validator": transcription_validator,
        "transcription_metrics_service_enhanced": transcription_metrics_service_enhanced,
        "transcription_state_manager": transcription_state_manager,
        "enhanced_speech_recognition_service": enhanced_speech_recognition_service,
        
        # Legacy Services (for backward compatibility)
        "transcription_factory": transcription_factory,
        "audio_processor": audio_processor,
        "provider_factory": provider_factory,
        "transcription_processor": transcription_processor,
        "notification_service": notification_service,
        "metrics_service": metrics_service,
        "orchestration_service": orchestration_service,
        
        # Command Handlers
        "set_speaker_aliases_handler": set_speaker_aliases_handler,
        "process_transcription_handler": process_transcription_handler,
    }
