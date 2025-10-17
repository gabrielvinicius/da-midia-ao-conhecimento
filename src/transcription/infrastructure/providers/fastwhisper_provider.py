# src/transcription/infrastructure/providers/fastwhisper_provider.py
"""
FastWhisper speech recognition provider - OCP and SRP compliance.
"""
import asyncio
import numpy as np
from typing import Dict, Any, List
from faster_whisper import WhisperModel

from src.transcription.domain.interfaces import TranscriptionConfiguration, AudioFormat
from src.transcription.infrastructure.providers.base_provider import (
    BaseSpeechRecognitionProvider, 
    SpeechRecognitionProviderError
)


class FastWhisperConfiguration(TranscriptionConfiguration):
    """Configuration for FastWhisper speech recognition - SRP compliance."""
    
    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        max_file_size: int = 100 * 1024 * 1024,  # 100MB
        sample_rate: int = 16000,
        beam_size: int = 5,
        vad_filter: bool = True,
        min_silence_duration_ms: int = 500
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.max_file_size = max_file_size
        self.sample_rate = sample_rate
        self.beam_size = beam_size
        self.vad_filter = vad_filter
        self.min_silence_duration_ms = min_silence_duration_ms
    
    def get_config(self) -> Dict[str, Any]:
        """Get configuration dictionary."""
        return {
            "model_size": self.model_size,
            "device": self.device,
            "compute_type": self.compute_type,
            "max_file_size": self.max_file_size,
            "sample_rate": self.sample_rate,
            "beam_size": self.beam_size,
            "vad_filter": self.vad_filter,
            "min_silence_duration_ms": self.min_silence_duration_ms
        }
    
    def validate_config(self) -> bool:
        """Validate configuration."""
        valid_models = ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"]
        valid_devices = ["cpu", "cuda"]
        valid_compute_types = ["int8", "int16", "float16", "float32"]
        
        return (
            self.model_size in valid_models and
            self.device in valid_devices and
            self.compute_type in valid_compute_types and
            self.max_file_size > 0 and
            self.sample_rate > 0 and
            self.beam_size > 0
        )
    
    def get_supported_formats(self) -> List[AudioFormat]:
        """Get supported audio formats."""
        return [
            AudioFormat.MP3,
            AudioFormat.WAV,
            AudioFormat.M4A,
            AudioFormat.FLAC,
            AudioFormat.OGG,
            AudioFormat.AAC
        ]
    
    def get_max_file_size(self) -> int:
        """Get maximum file size in bytes."""
        return self.max_file_size


class FastWhisperSpeechRecognitionProvider(BaseSpeechRecognitionProvider):
    """
    FastWhisper speech recognition provider.
    Follows OCP - can be extended without modification.
    """
    
    def __init__(self, config: FastWhisperConfiguration):
        super().__init__(config)
        self._config = config
        self._model = None
    
    @property
    def provider_name(self) -> str:
        """Provider identifier."""
        return "fastwhisper"
    
    def _initialize_provider(self) -> None:
        """Initialize FastWhisper model."""
        try:
            self._model = WhisperModel(
                self._config.model_size,
                device=self._config.device,
                compute_type=self._config.compute_type
            )
        except Exception as e:
            raise SpeechRecognitionProviderError(f"Failed to load FastWhisper model: {e}") from e
    
    async def _do_transcribe(self, audio_data: bytes, language: str) -> Dict[str, Any]:
        """Actual transcription implementation using FastWhisper."""
        try:
            # Decode audio to numpy array
            audio_array, sample_rate = await self._decode_audio_bytes(audio_data)
            
            # Perform transcription
            segments, info = await asyncio.to_thread(
                self._model.transcribe,
                audio_array,
                language=language if language != "auto" else None,
                beam_size=self._config.beam_size,
                vad_filter=self._config.vad_filter,
                vad_parameters=dict(min_silence_duration_ms=self._config.min_silence_duration_ms)
            )
            
            # Convert generator to list
            segments_list = list(segments)
            
            return self._format_fastwhisper_result(segments_list, info)
            
        except Exception as e:
            raise SpeechRecognitionProviderError(f"FastWhisper transcription failed: {e}") from e
    
    async def get_supported_languages(self) -> List[str]:
        """Get supported languages."""
        # FastWhisper supports the same languages as Whisper
        return [
            "en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh",
            "ar", "hi", "tr", "pl", "nl", "sv", "da", "no", "fi", "hu",
            "cs", "sk", "sl", "hr", "bg", "ro", "uk", "ca", "eu", "gl",
            "is", "mt", "cy", "ga", "gd", "br", "co", "la", "mi", "oc",
            "yi", "ne", "si", "my", "km", "lo", "bn", "ml", "ta", "te"
        ]
    
    def _supports_timestamps(self) -> bool:
        """Whether provider supports timestamps."""
        return True
    
    def _supports_speaker_diarization(self) -> bool:
        """Whether provider supports speaker diarization."""
        return False  # FastWhisper doesn't natively support speaker diarization
    
    def _supports_word_level_timestamps(self) -> bool:
        """Whether provider supports word-level timestamps."""
        return True
    
    async def _decode_audio_bytes(self, file_bytes: bytes) -> tuple[np.ndarray, int]:
        """Decode audio bytes using FFmpeg."""
        command = [
            'ffmpeg',
            '-i', 'pipe:0',  # Input from stdin
            '-f', 's16le',  # Output format: PCM signed 16-bit little-endian
            '-ac', '1',  # Single channel (mono)
            '-ar', str(self._config.sample_rate),  # Sample rate
            '-loglevel', 'error',  # Only log errors
            '-hide_banner',  # Hide banner info
            'pipe:1'  # Output to stdout
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate(input=file_bytes)
            await process.wait()

            if process.returncode != 0:
                err_msg = stderr.decode().strip() if stderr else f"FFmpeg error {process.returncode}"
                raise SpeechRecognitionProviderError(f"Audio decoding failed: {err_msg}")

            # Convert bytes to numpy int16 array, then normalize to float32
            audio_array = np.frombuffer(stdout, dtype=np.int16)
            audio_array = audio_array.astype(np.float32) / 32768.0  # Normalize to [-1, 1]
            
            return audio_array, self._config.sample_rate
            
        except Exception as e:
            raise SpeechRecognitionProviderError(f"Audio decoding failed: {e}") from e
    
    def _format_fastwhisper_result(self, segments_list: List, info) -> Dict[str, Any]:
        """Format FastWhisper result to standard structure."""
        formatted_segments = []
        full_text_parts = []
        
        for segment in segments_list:
            segment_text = segment.text.strip()
            full_text_parts.append(segment_text)
            
            formatted_segment = {
                "text": segment_text,
                "start": segment.start,
                "end": segment.end,
                "confidence": getattr(segment, 'avg_logprob', 0.0)
            }
            
            # Add word-level information if available
            if hasattr(segment, 'words') and segment.words:
                formatted_segment["words"] = [
                    {
                        "word": word.word,
                        "start": word.start,
                        "end": word.end,
                        "confidence": getattr(word, 'probability', 0.0)
                    }
                    for word in segment.words
                ]
            
            formatted_segments.append(formatted_segment)
        
        # Extract information from info object
        detected_language = getattr(info, 'language', 'unknown')
        language_probability = getattr(info, 'language_probability', 0.0)
        
        return {
            "text": " ".join(full_text_parts),
            "language": detected_language,
            "confidence": language_probability,
            "segments": formatted_segments,
            "processing_time": 0.0,  # FastWhisper doesn't provide this directly
            "fastwhisper_specific": {
                "model_size": self._config.model_size,
                "device": self._config.device,
                "compute_type": self._config.compute_type,
                "vad_filter": self._config.vad_filter,
                "beam_size": self._config.beam_size
            }
        }
    
    async def _detect_language(self, audio_data: bytes) -> str:
        """Detect language using FastWhisper."""
        try:
            # Use a small sample for language detection
            audio_array, _ = await self._decode_audio_bytes(audio_data[:1024*1024])  # First 1MB
            
            # Use transcribe with language detection
            segments, info = await asyncio.to_thread(
                self._model.transcribe,
                audio_array[:self._config.sample_rate * 30],  # First 30 seconds
                beam_size=1,  # Faster for detection
                vad_filter=False
            )
            
            # Extract detected language
            detected_language = getattr(info, 'language', 'en')
            return detected_language
            
        except Exception:
            # Fallback to English
            return "en"
    
    async def _get_provider_specific_capabilities(self) -> Dict[str, Any]:
        """Get FastWhisper-specific capabilities."""
        return {
            "model_size": self._config.model_size,
            "device": self._config.device,
            "compute_type": self._config.compute_type,
            "sample_rate": self._config.sample_rate,
            "supports_vad": True,
            "supports_beam_search": True,
            "supports_language_detection": True,
            "available_models": ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"],
            "available_devices": ["cpu", "cuda"],
            "available_compute_types": ["int8", "int16", "float16", "float32"]
        }