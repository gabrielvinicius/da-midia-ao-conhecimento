# src/transcription/infrastructure/factory.py
"""
Speech recognition provider factory implementation - DIP and OCP compliance.
"""
from typing import Dict, Type, Callable
from src.transcription.domain.interfaces import (
    SpeechRecognitionProviderFactory, 
    SpeechRecognitionProvider, 
    TranscriptionConfiguration
)
from src.transcription.infrastructure.providers.whisper_provider import (
    WhisperSpeechRecognitionProvider, 
    WhisperConfiguration
)
from src.transcription.infrastructure.providers.fastwhisper_provider import (
    FastWhisperSpeechRecognitionProvider, 
    FastWhisperConfiguration
)


class ConcreteSpeechRecognitionProviderFactory(SpeechRecognitionProviderFactory):
    """
    Concrete factory for creating speech recognition providers.
    Follows OCP - new providers can be added without modifying existing code.
    """
    
    def __init__(self):
        self._providers: Dict[str, Type[SpeechRecognitionProvider]] = {}
        self._config_factories: Dict[str, Callable[..., TranscriptionConfiguration]] = {}
        self._register_default_providers()
    
    def _register_default_providers(self) -> None:
        """Register default speech recognition providers."""
        self.register_provider(
            "whisper", 
            WhisperSpeechRecognitionProvider,
            WhisperConfiguration
        )
        self.register_provider(
            "fastwhisper", 
            FastWhisperSpeechRecognitionProvider,
            FastWhisperConfiguration
        )
    
    def register_provider(
        self, 
        provider_type: str, 
        provider_class: Type[SpeechRecognitionProvider],
        config_class: Type[TranscriptionConfiguration]
    ) -> None:
        """
        Register a new speech recognition provider.
        Enables extension without modification (OCP).
        """
        self._providers[provider_type] = provider_class
        self._config_factories[provider_type] = config_class
    
    def create_provider(
        self, 
        provider_type: str, 
        config: TranscriptionConfiguration
    ) -> SpeechRecognitionProvider:
        """Create speech recognition provider instance."""
        if provider_type not in self._providers:
            raise ValueError(f"Unknown speech recognition provider: {provider_type}")
        
        provider_class = self._providers[provider_type]
        return provider_class(config)
    
    def create_provider_with_params(
        self, 
        provider_type: str, 
        **config_params
    ) -> SpeechRecognitionProvider:
        """Create provider with configuration parameters."""
        if provider_type not in self._config_factories:
            raise ValueError(f"Unknown speech recognition provider: {provider_type}")
        
        config_class = self._config_factories[provider_type]
        config = config_class(**config_params)
        return self.create_provider(provider_type, config)
    
    def get_available_providers(self) -> list[str]:
        """Get list of available provider types."""
        return list(self._providers.keys())


# Global factory instance
_speech_recognition_factory = ConcreteSpeechRecognitionProviderFactory()


def get_speech_recognition_factory() -> SpeechRecognitionProviderFactory:
    """Get the global speech recognition factory instance."""
    return _speech_recognition_factory


def register_speech_recognition_provider(
    provider_type: str, 
    provider_class: Type[SpeechRecognitionProvider],
    config_class: Type[TranscriptionConfiguration]
) -> None:
    """
    Register a custom speech recognition provider globally.
    Allows third-party extensions (OCP).
    """
    _speech_recognition_factory.register_provider(provider_type, provider_class, config_class)