# src/transcription/__init__.py
"""
Transcription module following SOLID principles.

This module provides a clean, extensible speech recognition and transcription abstraction that follows:
- SRP: Each class has a single responsibility
- OCP: Easy to extend with new providers without modification
- LSP: All providers implement the same interface contract
- ISP: Segregated interfaces for different concerns
- DIP: High-level modules depend on abstractions

Usage:
    from src.transcription import get_transcription_orchestrator
    
    # Get orchestrator (auto-configured from environment)
    orchestrator = get_transcription_orchestrator(session)
    
    # Process audio transcription
    transcription = await orchestrator.process_transcription(
        media_id="123",
        audio_data=audio_bytes,
        language="en",
        provider="whisper",
        user_id="user123"
    )
    
    # Process video transcription
    transcription = await orchestrator.process_video_transcription(
        media_id="124",
        video_data=video_bytes,
        language="en",
        provider="fastwhisper",
        user_id="user123"
    )
    
    # Get existing transcription
    existing = await orchestrator.get_transcription("123")
"""

# Domain exports
from src.transcription.domain.transcription import Transcription, TranscriptionStatus
from src.transcription.domain.interfaces import (
    ITranscriptionRepository,
    SpeechRecognitionProvider,
    SpeechRecognitionProviderFactory,
    TranscriptionConfiguration,
    TranscriptionOrchestrator,
    AudioProcessor,
    TranscriptionValidator,
    AudioFormat
)

# Application exports
from src.transcription.application.commands.process_transcription_command import ProcessTranscriptionCommand
from src.transcription.application.commands.process_transcription_command_handler import ProcessTranscriptionCommandHandler
from src.transcription.application.commands.set_speaker_aliases_command import SetSpeakerAliasesCommand
from src.transcription.application.commands.set_speaker_aliases_command_handler import SetSpeakerAliasesCommandHandler
from src.transcription.application.services.audio_processor import DefaultAudioProcessor
from src.transcription.application.services.transcription_validator import DefaultTranscriptionValidator

# Infrastructure exports
from src.transcription.infrastructure.dependencies import (
    get_transcription_orchestrator,
    get_speech_recognition_factory_dep,
    get_transcription_logger_dep,
    get_transcription_metrics_dep,
    get_audio_processor_dep,
    get_transcription_validator_dep
)
from src.transcription.infrastructure.factory import register_speech_recognition_provider

# Provider implementations
from src.transcription.infrastructure.providers.whisper_provider import (
    WhisperSpeechRecognitionProvider, 
    WhisperConfiguration
)
from src.transcription.infrastructure.providers.fastwhisper_provider import (
    FastWhisperSpeechRecognitionProvider, 
    FastWhisperConfiguration
)

__all__ = [
    # Domain
    "Transcription",
    "TranscriptionStatus",
    "ITranscriptionRepository",
    "SpeechRecognitionProvider",
    "SpeechRecognitionProviderFactory",
    "TranscriptionConfiguration",
    "TranscriptionOrchestrator",
    "AudioProcessor",
    "TranscriptionValidator",
    "AudioFormat",
    
    # Application
    "ProcessTranscriptionCommand",
    "ProcessTranscriptionCommandHandler",
    "SetSpeakerAliasesCommand",
    "SetSpeakerAliasesCommandHandler",
    "DefaultAudioProcessor",
    "DefaultTranscriptionValidator",
    
    # Infrastructure
    "get_transcription_orchestrator",
    "get_speech_recognition_factory_dep",
    "get_transcription_logger_dep",
    "get_transcription_metrics_dep",
    "get_audio_processor_dep",
    "get_transcription_validator_dep",
    "register_speech_recognition_provider",
    
    # Providers
    "WhisperSpeechRecognitionProvider",
    "WhisperConfiguration",
    "FastWhisperSpeechRecognitionProvider",
    "FastWhisperConfiguration",
]
