# src/transcription/infrastructure/providers/base_provider.py
"""
Base implementation for speech recognition providers - Template Method pattern.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
import time

from src.transcription.domain.interfaces import (
    SpeechRecognitionProvider, 
    TranscriptionConfiguration,
    AudioFormat
)


class SpeechRecognitionProviderError(Exception):
    """Base exception for speech recognition provider errors."""
    pass


class BaseSpeechRecognitionProvider(SpeechRecognitionProvider):
    """
    Base speech recognition provider implementing common functionality.
    Follows Template Method pattern and OCP.
    """
    
    def __init__(self, config: TranscriptionConfiguration):
        self._config = config
        self._validate_configuration()
        self._initialize_provider()
    
    def _validate_configuration(self) -> None:
        """Validate provider configuration."""
        if not self._config.validate_config():
            raise SpeechRecognitionProviderError("Invalid transcription configuration")
    
    @abstractmethod
    def _initialize_provider(self) -> None:
        """Initialize provider-specific components."""
        pass
    
    async def transcribe(self, audio_data: bytes, language: str = "auto") -> Dict[str, Any]:
        """Template method for speech recognition."""
        try:
            # Pre-transcription hook
            await self._pre_transcribe(audio_data, language)
            
            # Input validation
            self._validate_input(audio_data, language)
            
            # Audio preprocessing
            processed_audio = await self._preprocess_audio(audio_data)
            
            # Language detection/validation
            validated_language = await self._validate_and_detect_language(language, processed_audio)
            
            # Actual transcription (implemented by subclasses)
            raw_result = await self._do_transcribe(processed_audio, validated_language)
            
            # Post-processing
            structured_result = await self._postprocess_result(raw_result, validated_language)
            
            # Post-transcription hook
            await self._post_transcribe(audio_data, language, structured_result)
            
            return structured_result
            
        except Exception as e:
            await self._handle_transcription_error(audio_data, language, e)
            raise SpeechRecognitionProviderError(f"Transcription failed") from e
    
    def _validate_input(self, audio_data: bytes, language: str) -> None:
        """Validate input audio and language."""
        if not audio_data:
            raise SpeechRecognitionProviderError("Audio data is empty")
        
        max_size = self._config.get_max_file_size()
        if len(audio_data) > max_size:
            raise SpeechRecognitionProviderError(
                f"Audio size {len(audio_data)} exceeds maximum {max_size}"
            )
    
    async def get_capabilities(self) -> Dict[str, Any]:
        """Get provider capabilities."""
        return {
            "provider_name": self.provider_name,
            "supported_languages": await self.get_supported_languages(),
            "supported_formats": [fmt.value for fmt in self._config.get_supported_formats()],
            "max_file_size": self._config.get_max_file_size(),
            "supports_timestamps": self._supports_timestamps(),
            "supports_speaker_diarization": self._supports_speaker_diarization(),
            "supports_word_level_timestamps": self._supports_word_level_timestamps(),
            **await self._get_provider_specific_capabilities()
        }
    
    # Abstract methods to be implemented by subclasses
    @abstractmethod
    async def _do_transcribe(self, audio_data: bytes, language: str) -> Dict[str, Any]:
        """Actual transcription implementation."""
        pass
    
    @abstractmethod
    async def get_supported_languages(self) -> List[str]:
        """Get supported languages."""
        pass
    
    @abstractmethod
    def _supports_timestamps(self) -> bool:
        """Whether provider supports timestamps."""
        pass
    
    @abstractmethod
    def _supports_speaker_diarization(self) -> bool:
        """Whether provider supports speaker diarization."""
        pass
    
    @abstractmethod
    def _supports_word_level_timestamps(self) -> bool:
        """Whether provider supports word-level timestamps."""
        pass
    
    # Hook methods (can be overridden by subclasses)
    async def _pre_transcribe(self, audio_data: bytes, language: str) -> None:
        """Hook called before transcription."""
        pass
    
    async def _post_transcribe(
        self, 
        audio_data: bytes, 
        language: str, 
        result: Dict[str, Any]
    ) -> None:
        """Hook called after successful transcription."""
        pass
    
    async def _preprocess_audio(self, audio_data: bytes) -> bytes:
        """Preprocess audio data."""
        # Default implementation: return as-is
        return audio_data
    
    async def _validate_and_detect_language(
        self, 
        language: str, 
        audio_data: bytes
    ) -> str:
        """Validate and potentially detect language."""
        if language == "auto":
            # Try to detect language (default implementation)
            return await self._detect_language(audio_data)
        
        # Validate provided language
        supported_languages = await self.get_supported_languages()
        if language not in supported_languages:
            # Fallback to auto-detection or default
            return await self._detect_language(audio_data)
        
        return language
    
    async def _detect_language(self, audio_data: bytes) -> str:
        """Detect language from audio (default implementation)."""
        # Default implementation: return English
        return "en"
    
    async def _postprocess_result(
        self, 
        raw_result: Dict[str, Any], 
        language: str
    ) -> Dict[str, Any]:
        """Post-process transcription result to standard format."""
        # Ensure standard structure
        structured_result = {
            "text": raw_result.get("text", ""),
            "language": language,
            "confidence": raw_result.get("confidence", 0.0),
            "segments": raw_result.get("segments", []),
            "metadata": {
                "provider": self.provider_name,
                "timestamp": time.time(),
                "processing_time": raw_result.get("processing_time", 0.0)
            }
        }
        
        # Add provider-specific fields
        for key, value in raw_result.items():
            if key not in structured_result:
                structured_result["metadata"][key] = value
        
        return structured_result
    
    async def _handle_transcription_error(
        self, 
        audio_data: bytes, 
        language: str, 
        error: Exception
    ) -> None:
        """Handle transcription errors."""
        pass
    
    async def _get_provider_specific_capabilities(self) -> Dict[str, Any]:
        """Get provider-specific capabilities."""
        return {}
    
    def _estimate_audio_duration(self, audio_data: bytes) -> float:
        """Estimate audio duration (rough calculation)."""
        # Very rough estimation - should be overridden by providers
        # Assumes 16-bit PCM at 16kHz
        sample_rate = 16000
        bytes_per_sample = 2
        return len(audio_data) / (sample_rate * bytes_per_sample)
    
    def _create_segment(
        self, 
        text: str, 
        start: float, 
        end: float, 
        confidence: float = 0.0
    ) -> Dict[str, Any]:
        """Create a standard segment structure."""
        return {
            "text": text,
            "start": start,
            "end": end,
            "confidence": confidence
        }