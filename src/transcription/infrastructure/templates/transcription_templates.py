"""
Transcription Template Methods using Template Method Pattern
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import io

from src.shared.patterns.template_method import TemplateMethodBase, ProcessingResult, TemplateMethodFactory
from src.transcription.domain.transcription import Transcription


class AudioFormat(str, Enum):
    """Supported audio formats"""
    WAV = "wav"
    MP3 = "mp3"
    M4A = "m4a"
    FLAC = "flac"
    OGG = "ogg"


@dataclass
class TranscriptionInput:
    """Input data for transcription template methods"""
    audio_data: bytes
    language: str = "en"
    audio_format: AudioFormat = AudioFormat.WAV
    sample_rate: int = 16000
    channels: int = 1
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseTranscriptionTemplate(TemplateMethodBase[TranscriptionInput, Transcription]):
    """
    Base template for all transcription algorithms.
    Defines the common structure for transcription processing.
    """
    
    def __init__(self, provider_name: str, model_name: str = None):
        super().__init__(f"{provider_name}TranscriptionTemplate")
        self.provider_name = provider_name
        self.model_name = model_name or "default"
        self.processed_audio = None
        self.transcription_result = None
    
    async def _initialize(self, input_data: TranscriptionInput, options: Dict[str, Any]) -> Any:
        """Initialize transcription session"""
        self.processing_result.add_metadata("provider", self.provider_name)
        self.processing_result.add_metadata("model", self.model_name)
        self.processing_result.add_metadata("language", input_data.language)
        self.processing_result.add_metadata("audio_format", input_data.audio_format.value)
        
        # Initialize provider-specific resources
        await self._initialize_provider(input_data, options)
        
        return {
            "provider": self.provider_name,
            "model": self.model_name,
            "session_id": f"{self.provider_name}_{hash(input_data.audio_data) % 10000}"
        }
    
    async def _validate(self, input_data: TranscriptionInput, options: Dict[str, Any]) -> bool:
        """Validate audio input"""
        
        # Check audio data
        if not input_data.audio_data or len(input_data.audio_data) == 0:
            self.processing_result.add_error("Audio data is empty")
            return False
        
        # Check audio size limits
        max_size = options.get("max_audio_size_mb", 25) * 1024 * 1024
        if len(input_data.audio_data) > max_size:
            self.processing_result.add_error(
                f"Audio size {len(input_data.audio_data)} exceeds limit {max_size}"
            )
            return False
        
        # Check language support
        supported_languages = await self._get_supported_languages()
        if input_data.language not in supported_languages:
            self.processing_result.add_error(
                f"Language '{input_data.language}' not supported. "
                f"Supported: {', '.join(supported_languages)}"
            )
            return False
        
        # Provider-specific validation
        return await self._validate_provider_specific(input_data, options)
    
    async def _preprocess(self, input_data: TranscriptionInput, options: Dict[str, Any]) -> Any:
        """Preprocess audio data"""
        
        # Convert audio format if needed
        converted_audio = await self._convert_audio_format(input_data, options)
        
        # Apply audio enhancements
        enhanced_audio = await self._enhance_audio(converted_audio, options)
        
        # Normalize audio
        self.processed_audio = await self._normalize_audio(enhanced_audio, options)
        
        self.processing_result.add_metadata("preprocessing", {
            "original_size": len(input_data.audio_data),
            "processed_size": len(self.processed_audio),
            "format_converted": converted_audio != input_data.audio_data,
            "enhanced": enhanced_audio != converted_audio,
            "normalized": True
        })
        
        return self.processed_audio
    
    async def _process(self, input_data: TranscriptionInput, options: Dict[str, Any]) -> Transcription:
        """Core transcription processing - implemented by subclasses"""
        
        # Use processed audio if available, otherwise original
        audio_to_process = self.processed_audio or input_data.audio_data
        
        # Provider-specific transcription
        transcription_text = await self._perform_transcription(
            audio_to_process, 
            input_data.language, 
            options
        )
        
        # Create transcription object
        self.transcription_result = Transcription(
            text=transcription_text,
            language=input_data.language,
            confidence=options.get("confidence", 0.95),
            provider=self.provider_name,
            model=self.model_name,
            metadata=input_data.metadata
        )
        
        return self.transcription_result
    
    async def _postprocess(self, input_data: TranscriptionInput, options: Dict[str, Any]) -> Any:
        """Post-process transcription results"""
        
        if not self.transcription_result:
            return None
        
        # Apply text cleaning
        cleaned_text = await self._clean_transcription_text(
            self.transcription_result.text, 
            options
        )
        
        # Extract speaker information if available
        speaker_info = await self._extract_speaker_information(
            self.transcription_result, 
            options
        )
        
        # Add timestamps if supported
        timestamps = await self._extract_timestamps(
            self.transcription_result,
            options
        )
        
        # Update transcription with post-processed data
        self.transcription_result.text = cleaned_text
        if speaker_info:
            self.transcription_result.speakers = speaker_info
        if timestamps:
            self.transcription_result.timestamps = timestamps
        
        self.processing_result.add_metadata("postprocessing", {
            "text_cleaned": cleaned_text != self.transcription_result.text,
            "speakers_detected": bool(speaker_info),
            "timestamps_extracted": bool(timestamps)
        })
        
        return self.transcription_result
    
    async def _finalize(self, input_data: TranscriptionInput, options: Dict[str, Any]) -> Transcription:
        """Finalize transcription and cleanup"""
        
        if not self.transcription_result:
            raise ValueError("No transcription result available")
        
        # Add final metadata
        self.transcription_result.processing_metadata = {
            "provider": self.provider_name,
            "model": self.model_name,
            "processing_time": self.processing_result.processing_time,
            "audio_duration": self._estimate_audio_duration(input_data),
            "confidence": self.transcription_result.confidence
        }
        
        # Cleanup provider resources
        await self._cleanup_provider()
        
        # Set final result
        self.processing_result.result = self.transcription_result
        
        return self.transcription_result
    
    def _should_preprocess(self) -> bool:
        """Enable preprocessing by default"""
        return True
    
    def _should_postprocess(self) -> bool:
        """Enable postprocessing by default"""
        return True
    
    # Abstract methods for provider-specific implementation
    
    async def _initialize_provider(self, input_data: TranscriptionInput, options: Dict[str, Any]) -> None:
        """Initialize provider-specific resources. Override in subclasses."""
        pass
    
    async def _get_supported_languages(self) -> list[str]:
        """Get supported languages. Override in subclasses."""
        return ["en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh"]
    
    async def _validate_provider_specific(self, input_data: TranscriptionInput, options: Dict[str, Any]) -> bool:
        """Provider-specific validation. Override in subclasses."""
        return True
    
    async def _perform_transcription(
        self, 
        audio_data: bytes, 
        language: str, 
        options: Dict[str, Any]
    ) -> str:
        """Perform actual transcription. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement _perform_transcription")
    
    async def _cleanup_provider(self) -> None:
        """Cleanup provider resources. Override in subclasses."""
        pass
    
    # Helper methods with default implementations
    
    async def _convert_audio_format(self, input_data: TranscriptionInput, options: Dict[str, Any]) -> bytes:
        """Convert audio format if needed"""
        target_format = options.get("target_format", AudioFormat.WAV)
        
        if input_data.audio_format == target_format:
            return input_data.audio_data
        
        # Basic format conversion (in practice, use ffmpeg or similar)
        self.processing_result.add_metadata("format_conversion", {
            "from": input_data.audio_format.value,
            "to": target_format.value
        })
        
        return input_data.audio_data  # Placeholder implementation
    
    async def _enhance_audio(self, audio_data: bytes, options: Dict[str, Any]) -> bytes:
        """Apply audio enhancements"""
        if not options.get("enhance_audio", False):
            return audio_data
        
        # Apply noise reduction, normalization, etc.
        # Placeholder implementation
        return audio_data
    
    async def _normalize_audio(self, audio_data: bytes, options: Dict[str, Any]) -> bytes:
        """Normalize audio levels"""
        if not options.get("normalize_audio", True):
            return audio_data
        
        # Audio normalization logic
        # Placeholder implementation
        return audio_data
    
    async def _clean_transcription_text(self, text: str, options: Dict[str, Any]) -> str:
        """Clean transcription text"""
        if not options.get("clean_text", True):
            return text
        
        import re
        
        # Remove multiple spaces
        cleaned = re.sub(r'\s+', ' ', text)
        
        # Remove filler words if requested
        if options.get("remove_fillers", False):
            fillers = ["um", "uh", "er", "ah", "like", "you know"]
            for filler in fillers:
                cleaned = re.sub(rf'\b{filler}\b', '', cleaned, flags=re.IGNORECASE)
                cleaned = re.sub(r'\s+', ' ', cleaned)
        
        return cleaned.strip()
    
    async def _extract_speaker_information(self, transcription: Transcription, options: Dict[str, Any]) -> Optional[Dict]:
        """Extract speaker information - override in subclasses that support it"""
        return None
    
    async def _extract_timestamps(self, transcription: Transcription, options: Dict[str, Any]) -> Optional[list]:
        """Extract timestamps - override in subclasses that support it"""
        return None
    
    def _estimate_audio_duration(self, input_data: TranscriptionInput) -> float:
        """Estimate audio duration from data size"""
        # Rough estimation: 16kHz, 16-bit, mono = 32KB per second
        bytes_per_second = input_data.sample_rate * 2 * input_data.channels
        return len(input_data.audio_data) / bytes_per_second


class WhisperTranscriptionTemplate(BaseTranscriptionTemplate):
    """Whisper-specific transcription template"""
    
    def __init__(self, model_size: str = "base"):
        super().__init__("whisper", model_size)
        self.model_size = model_size
        self.whisper_model = None
    
    async def _initialize_provider(self, input_data: TranscriptionInput, options: Dict[str, Any]) -> None:
        """Initialize Whisper model"""
        try:
            # In practice, load actual Whisper model
            self.whisper_model = f"whisper_{self.model_size}_model"
            self.processing_result.add_metadata("whisper_model_loaded", True)
        except Exception as e:
            self.processing_result.add_error(f"Failed to load Whisper model: {e}")
    
    async def _get_supported_languages(self) -> list[str]:
        """Whisper supports many languages"""
        return [
            "en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh", 
            "ar", "hi", "tr", "pl", "nl", "sv", "da", "no", "fi"
        ]
    
    async def _perform_transcription(
        self, 
        audio_data: bytes, 
        language: str, 
        options: Dict[str, Any]
    ) -> str:
        """Perform Whisper transcription"""
        if not self.whisper_model:
            raise ValueError("Whisper model not initialized")
        
        # Whisper-specific processing
        # In practice, use actual Whisper API
        transcription_text = f"[Whisper {self.model_size}] Transcribed audio in {language}"
        
        self.processing_result.add_metadata("whisper_processing", {
            "model_size": self.model_size,
            "language": language,
            "audio_length": len(audio_data)
        })
        
        return transcription_text
    
    async def _extract_timestamps(self, transcription: Transcription, options: Dict[str, Any]) -> Optional[list]:
        """Whisper supports word-level timestamps"""
        if not options.get("word_timestamps", False):
            return None
        
        # Mock timestamp data
        words = transcription.text.split()
        timestamps = []
        current_time = 0.0
        
        for word in words:
            timestamps.append({
                "word": word,
                "start": current_time,
                "end": current_time + 0.5,
                "confidence": 0.95
            })
            current_time += 0.6
        
        return timestamps


class FastWhisperTranscriptionTemplate(WhisperTranscriptionTemplate):
    """FastWhisper-specific transcription template"""
    
    def __init__(self, model_size: str = "base", device: str = "auto"):
        super().__init__(model_size)
        self.name = f"FastWhisper{model_size}TranscriptionTemplate"
        self.provider_name = "fast_whisper"
        self.device = device
    
    async def _initialize_provider(self, input_data: TranscriptionInput, options: Dict[str, Any]) -> None:
        """Initialize FastWhisper model"""
        try:
            # In practice, load actual FastWhisper model
            self.whisper_model = f"fast_whisper_{self.model_size}_model"
            self.processing_result.add_metadata("fast_whisper_device", self.device)
            self.processing_result.add_metadata("fast_whisper_model_loaded", True)
        except Exception as e:
            self.processing_result.add_error(f"Failed to load FastWhisper model: {e}")
    
    async def _perform_transcription(
        self, 
        audio_data: bytes, 
        language: str, 
        options: Dict[str, Any]
    ) -> str:
        """Perform FastWhisper transcription with optimizations"""
        if not self.whisper_model:
            raise ValueError("FastWhisper model not initialized")
        
        # FastWhisper-specific optimizations
        batch_size = options.get("batch_size", 16)
        beam_size = options.get("beam_size", 5)
        
        transcription_text = f"[FastWhisper {self.model_size}] Optimized transcription in {language}"
        
        self.processing_result.add_metadata("fast_whisper_processing", {
            "model_size": self.model_size,
            "device": self.device,
            "batch_size": batch_size,
            "beam_size": beam_size,
            "language": language
        })
        
        return transcription_text


class HuggingFaceTranscriptionTemplate(BaseTranscriptionTemplate):
    """HuggingFace-specific transcription template"""
    
    def __init__(self, model_name: str = "wav2vec2-base-960h"):
        super().__init__("huggingface", model_name)
        self.hf_model = None
        self.hf_processor = None
    
    async def _initialize_provider(self, input_data: TranscriptionInput, options: Dict[str, Any]) -> None:
        """Initialize HuggingFace model"""
        try:
            # In practice, load actual HuggingFace model
            self.hf_model = f"hf_model_{self.model_name}"
            self.hf_processor = f"hf_processor_{self.model_name}"
            self.processing_result.add_metadata("hf_model_loaded", True)
        except Exception as e:
            self.processing_result.add_error(f"Failed to load HuggingFace model: {e}")
    
    async def _get_supported_languages(self) -> list[str]:
        """HuggingFace model specific languages"""
        if "multilingual" in self.model_name:
            return ["en", "es", "fr", "de", "it", "pt"]
        else:
            return ["en"]  # Most models are English-only
    
    async def _perform_transcription(
        self, 
        audio_data: bytes, 
        language: str, 
        options: Dict[str, Any]
    ) -> str:
        """Perform HuggingFace transcription"""
        if not self.hf_model:
            raise ValueError("HuggingFace model not initialized")
        
        # HuggingFace-specific processing
        transcription_text = f"[HuggingFace {self.model_name}] Transcribed audio"
        
        self.processing_result.add_metadata("hf_processing", {
            "model_name": self.model_name,
            "language": language,
            "supports_multilingual": "multilingual" in self.model_name
        })
        
        return transcription_text


# Register templates in factory
def register_transcription_templates():
    """Register all transcription templates"""
    
    # Whisper templates
    TemplateMethodFactory.register_template(
        "whisper_tiny", 
        lambda: WhisperTranscriptionTemplate("tiny")
    )
    TemplateMethodFactory.register_template(
        "whisper_base", 
        lambda: WhisperTranscriptionTemplate("base")
    )
    TemplateMethodFactory.register_template(
        "whisper_small", 
        lambda: WhisperTranscriptionTemplate("small")
    )
    TemplateMethodFactory.register_template(
        "whisper_medium", 
        lambda: WhisperTranscriptionTemplate("medium")
    )
    TemplateMethodFactory.register_template(
        "whisper_large", 
        lambda: WhisperTranscriptionTemplate("large")
    )
    
    # FastWhisper templates
    TemplateMethodFactory.register_template(
        "fast_whisper_base", 
        lambda: FastWhisperTranscriptionTemplate("base")
    )
    TemplateMethodFactory.register_template(
        "fast_whisper_large", 
        lambda: FastWhisperTranscriptionTemplate("large", "cuda")
    )
    
    # HuggingFace templates
    TemplateMethodFactory.register_template(
        "wav2vec2_base", 
        lambda: HuggingFaceTranscriptionTemplate("wav2vec2-base-960h")
    )
    TemplateMethodFactory.register_template(
        "wav2vec2_large", 
        lambda: HuggingFaceTranscriptionTemplate("wav2vec2-large-960h")
    )