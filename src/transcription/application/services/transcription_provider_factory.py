# src/transcription/application/services/transcription_provider_factory.py
"""
Transcription Provider Factory following OCP and DIP principles.
Open for extension with new providers, depends on abstractions.
"""
from typing import Dict

from src.transcription.domain.interfaces import SpeechRecognitionService
# Import providers dynamically to avoid import errors during testing
# from src.transcription.infrastructure.whisper_speech_recognition import WhisperSpeechRecognition
# from src.transcription.infrastructure.fastwhisper_speech_recognition import FastWhisperSpeechRecognition
# from src.transcription.infrastructure.huggingface_speech_recognition import HuggingFaceSpeechRecognition


class TranscriptionProviderFactory:
    """
    Factory for creating speech recognition services.
    Follows OCP: Easy to extend with new providers.
    Follows DIP: Returns interfaces, not concrete implementations.
    """
    
    def __init__(self):
        self._providers: Dict[str, type] = {}
        # Register providers dynamically to avoid import issues
        self._register_default_providers()
    
    def create_speech_service(self, provider: str) -> SpeechRecognitionService:
        """Create a speech recognition service for the specified provider."""
        if provider not in self._providers:
            raise ValueError(f"Unknown transcription provider: {provider}")
        
        provider_class = self._providers[provider]
        return provider_class()
    
    def register_provider(self, name: str, provider_class: type):
        """Register a new speech recognition provider."""
        if not issubclass(provider_class, SpeechRecognitionService):
            raise ValueError("Provider must implement SpeechRecognitionService interface")
        
        self._providers[name] = provider_class
    
    def get_available_providers(self) -> list:
        """Get list of available provider names."""
        return list(self._providers.keys())
    
    def _register_default_providers(self):
        """Register default providers with error handling."""
        try:
            from src.transcription.infrastructure.whisper_speech_recognition import WhisperSpeechRecognition
            self._providers["whisper"] = WhisperSpeechRecognition
        except ImportError:
            pass
        
        try:
            from src.transcription.infrastructure.fastwhisper_speech_recognition import FastWhisperSpeechRecognition
            self._providers["fastwhisper"] = FastWhisperSpeechRecognition
        except ImportError:
            pass
        
        try:
            from src.transcription.infrastructure.huggingface_speech_recognition import HuggingFaceSpeechRecognition
            self._providers["huggingface"] = HuggingFaceSpeechRecognition
        except ImportError:
            pass