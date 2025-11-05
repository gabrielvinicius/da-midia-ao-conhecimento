# src/transcription/infrastructure/whisper_speech_recognition.py
import io
import logging
import os
import tempfile
from typing import Optional

import av
import numpy as np
import resampy
import whisper

from src.media_processing.transcription.infrastructure.dependencies import (
    register_speech_recognition,
)

logger = logging.getLogger(__name__)


@register_speech_recognition("whisper")
class WhisperTranscriber:
    def __init__(self, model_name: str = "base"):
        self.model = whisper.load_model(model_name)
        self.sample_rate = 16000  # Whisper expects 16kHz audio

    @property
    def provider_name(self) -> str:
        return "whisper"

    async def transcribe(self, file: bytes, language: str = "en") -> Optional[str]:
        """Transcribes an audio file and returns the transcribed text as a string."""
        path = None
        try:
            path = await self._decode_file_bytes(file)
            result = self.model.transcribe(path, language=language)
            # Return only the text content for the v1 pipeline
            return result["text"]
        except Exception as e:
            logger.error(f"Transcription failed: {str(e)}")
            raise RuntimeError(f"Transcription error: {str(e)}")
        finally:
            if path and os.path.exists(path):
                os.unlink(path)

    async def _decode_audio_bytes(self, file_bytes: bytes) -> np.ndarray:
        # ... (implementation remains the same)
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

            if original_rate != self.sample_rate:
                audio = resampy.resample(audio, original_rate, self.sample_rate)

            audio /= np.max(np.abs(audio)) + 1e-9  # Normalize

            return audio

        except Exception as e:
            logger.error(f"Audio decoding from video/audio failed: {str(e)}")
            raise RuntimeError(f"Audio decoding error: {str(e)}")

    async def _decode_file_bytes(self, file_bytes: bytes) -> str:
        tmp = tempfile.NamedTemporaryFile(suffix=".tmp", delete=False)
        tmp.write(file_bytes)
        tmp.flush()
        tmp.close()
        return tmp.name
