# src/transcription/infrastructure/providers/whisper_provider.py
"""Whisper speech recognition provider - OCP and SRP compliance.
"""
import asyncio
import io
import os
import tempfile
from typing import Any, Dict, List

import av
import numpy as np
import resampy
import whisper


class WhisperConfiguration:
    """Configuration for Whisper speech recognition - SRP compliance."""

    def __init__(
        self,
        model_name: str = "base",
        max_file_size: int = 100 * 1024 * 1024,  # 100MB
        sample_rate: int = 16000,
        enable_word_timestamps: bool = False,
        enable_speaker_detection: bool = False
    ):
        self.model_name = model_name
        self.max_file_size = max_file_size
        self.sample_rate = sample_rate
        self.enable_word_timestamps = enable_word_timestamps
        self.enable_speaker_detection = enable_speaker_detection

    def get_config(self) -> Dict[str, Any]:
        """Get configuration dictionary."""
        return {
            "model_name": self.model_name,
            "max_file_size": self.max_file_size,
            "sample_rate": self.sample_rate,
            "enable_word_timestamps": self.enable_word_timestamps,
            "enable_speaker_detection": self.enable_speaker_detection
        }

    def validate_config(self) -> bool:
        """Validate configuration."""
        valid_models = ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"]
        return (
            self.model_name in valid_models and
            self.max_file_size > 0 and
            self.sample_rate > 0
        )



    def get_max_file_size(self) -> int:
        """Get maximum file size in bytes."""
        return self.max_file_size


class WhisperSpeechRecognitionProvider:
    """Whisper speech recognition provider.
    Follows OCP - can be extended without modification.
    """

    def __init__(self, config: WhisperConfiguration):
        super().__init__(config)
        self._config = config
        self._model = None

    @property
    def provider_name(self) -> str:
        """Provider identifier."""
        return "whisper"

    def _initialize_provider(self) -> None:
        """Initialize Whisper model."""
        try:
            self._model = whisper.load_model(self._config.model_name)
        except Exception as e:
            raise SpeechRecognitionProviderError(f"Failed to load Whisper model: {e}") from e

    async def _do_transcribe(self, audio_data: bytes, language: str) -> Dict[str, Any]:
        """Actual transcription implementation using Whisper."""
        temp_file_path = None
        try:
            # Save audio to temporary file (Whisper expects file path)
            temp_file_path = await self._save_audio_to_temp_file(audio_data)

            # Perform transcription
            result = await asyncio.to_thread(
                self._model.transcribe,
                temp_file_path,
                language=language if language != "auto" else None,
                word_timestamps=self._config.enable_word_timestamps,
                verbose=False
            )

            return self._format_whisper_result(result)

        except Exception as e:
            raise SpeechRecognitionProviderError(f"Whisper transcription failed: {e}") from e
        finally:
            # Clean up temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    async def get_supported_languages(self) -> List[str]:
        """Get supported languages."""
        # Whisper supports many languages
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
        return False  # Whisper doesn't natively support speaker diarization

    def _supports_word_level_timestamps(self) -> bool:
        """Whether provider supports word-level timestamps."""
        return True

    async def _preprocess_audio(self, audio_data: bytes) -> bytes:
        """Preprocess audio for Whisper."""
        try:
            # Decode and normalize audio
            audio_array = await self._decode_audio_bytes(audio_data)

            # Convert back to bytes if needed
            return audio_data  # For now, return original

        except Exception:
            # If preprocessing fails, use original
            return audio_data

    async def _detect_language(self, audio_data: bytes) -> str:
        """Detect language using Whisper."""
        try:
            temp_file_path = await self._save_audio_to_temp_file(audio_data)

            # Use Whisper's language detection
            audio = whisper.load_audio(temp_file_path)
            audio = whisper.pad_or_trim(audio)
            mel = whisper.log_mel_spectrogram(audio).to(self._model.device)

            _, probs = self._model.detect_language(mel)
            detected_language = max(probs, key=probs.get)

            # Clean up
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

            return detected_language

        except Exception:
            # Fallback to English
            return "en"

    async def _save_audio_to_temp_file(self, audio_data: bytes) -> str:
        """Save audio data to temporary file."""
        temp_file = tempfile.NamedTemporaryFile(suffix=".tmp", delete=False)
        temp_file.write(audio_data)
        temp_file.flush()
        temp_file.close()
        return temp_file.name

    async def _decode_audio_bytes(self, file_bytes: bytes) -> np.ndarray:
        """Decode audio bytes to numpy array."""
        try:
            buffer = io.BytesIO(file_bytes)
            container = av.open(buffer)

            audio_stream = next((s for s in container.streams if s.type == 'audio'), None)
            if audio_stream is None:
                raise ValueError("No audio stream found in the input file")

            frames = []
            for packet in container.demux(audio_stream):
                for frame in packet.decode():
                    samples = frame.to_ndarray()
                    if samples.ndim > 1:
                        samples = np.mean(samples, axis=0)  # Convert to mono
                    frames.append(samples)

            if not frames:
                raise ValueError("No audio frames found")

            audio = np.concatenate(frames).astype(np.float32)
            original_rate = audio_stream.rate

            # Resample if needed
            if original_rate != self._config.sample_rate:
                audio = resampy.resample(audio, original_rate, self._config.sample_rate)

            # Normalize
            audio /= np.max(np.abs(audio)) + 1e-9

            return audio

        except Exception as e:
            raise SpeechRecognitionProviderError(f"Audio decoding failed: {e}") from e

    def _format_whisper_result(self, whisper_result: Dict[str, Any]) -> Dict[str, Any]:
        """Format Whisper result to standard structure."""
        segments = []

        # Process segments if available
        if "segments" in whisper_result:
            for segment in whisper_result["segments"]:
                formatted_segment = {
                    "text": segment.get("text", "").strip(),
                    "start": segment.get("start", 0.0),
                    "end": segment.get("end", 0.0),
                    "confidence": segment.get("avg_logprob", 0.0)
                }

                # Add word-level timestamps if available
                if "words" in segment and self._config.enable_word_timestamps:
                    formatted_segment["words"] = [
                        {
                            "word": word.get("word", ""),
                            "start": word.get("start", 0.0),
                            "end": word.get("end", 0.0),
                            "confidence": word.get("probability", 0.0)
                        }
                        for word in segment["words"]
                    ]

                segments.append(formatted_segment)

        return {
            "text": whisper_result.get("text", "").strip(),
            "language": whisper_result.get("language", "unknown"),
            "confidence": self._calculate_overall_confidence(segments),
            "segments": segments,
            "processing_time": 0.0,  # Whisper doesn't provide this directly
            "whisper_specific": {
                "model": self._config.model_name,
                "no_speech_prob": whisper_result.get("no_speech_prob", 0.0)
            }
        }

    def _calculate_overall_confidence(self, segments: List[Dict[str, Any]]) -> float:
        """Calculate overall confidence from segments."""
        if not segments:
            return 0.0

        confidences = [seg.get("confidence", 0.0) for seg in segments]
        return sum(confidences) / len(confidences)

    async def _get_provider_specific_capabilities(self) -> Dict[str, Any]:
        """Get Whisper-specific capabilities."""
        return {
            "model_name": self._config.model_name,
            "sample_rate": self._config.sample_rate,
            "supports_language_detection": True,
            "supports_no_speech_detection": True,
            "available_models": ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"]
        }
