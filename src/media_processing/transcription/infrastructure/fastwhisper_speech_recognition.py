import asyncio
import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
from faster_whisper import WhisperModel

from src.media_processing.transcription.infrastructure.dependencies import (
    register_speech_recognition,
)

logger = logging.getLogger(__name__)


@register_speech_recognition("fastwhisper")
class FastWhisperTranscriber:
    def __init__(
            self,
            model_size: str = "base",
            device: str = "cpu",
            compute_type: str = "int8",
            language: Optional[str] = "en",
    ):
        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type
        )
        self.language = language
        self.sample_rate = 16000

    @property
    def provider_name(self) -> str:
        return "fastwhisper"

    async def transcribe(self, file: bytes, language: str = "en") -> Dict[str, object]:
        try:
            lang_to_use = language or self.language
            audio_array, _ = await self._decode_audio_bytes(file)
            return await self._transcribe_audio(audio_array, lang_to_use)
        except Exception as e:
            logger.error(
                "fastwhisper.transcription_failed",
                extra={"error": str(e)},
                exc_info=True,
            )
            raise RuntimeError(f"Transcription error: {str(e)}")

    async def _transcribe_audio(self, audio: np.ndarray, language: str) -> Dict[str, object]:
        loop = asyncio.get_running_loop()

        def _run():
            segments_iter, info = self.model.transcribe(
                audio,
                language=language,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500),
            )
            text_parts: List[str] = []
            segments_payload: List[Dict[str, float | str]] = []
            for segment in segments_iter:
                text_parts.append(segment.text)
                segments_payload.append(
                    {
                        "start": float(segment.start or 0.0),
                        "end": float(segment.end or 0.0),
                        "text": segment.text,
                    }
                )
            return {
                "text": " ".join(text_parts).strip(),
                "segments": segments_payload,
                "language": language,
                "provider": self.provider_name,
                "duration": getattr(info, "duration", None),
            }

        return await loop.run_in_executor(None, _run)

    async def _decode_audio_bytes(self, file_bytes: bytes) -> Tuple[np.ndarray, int]:
        """Decodes audio bytes to a numpy array using FFmpeg."""
        command = [
            'ffmpeg',
            '-i', 'pipe:0',  # Input from stdin
            '-f', 's16le',  # Output format: PCM signed 16-bit little-endian
            '-ac', '1',  # Single channel (mono)
            '-ar', str(self.sample_rate),  # Sample rate
            '-loglevel', 'error',  # Only log errors
            '-hide_banner',  # Hide banner info
            'pipe:1'  # Output to stdout
        ]

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
            raise RuntimeError(f"Audio decoding failed: {err_msg}")

        # Convert bytes to numpy int16 array
        audio_array = np.frombuffer(stdout, dtype=np.int16).astype(np.float32)
        # Normalize to [-1, 1] expected by VAD/whisper pipelines
        denom = max(np.abs(audio_array).max(), 1e-9)
        audio_array = audio_array / denom
        return audio_array, self.sample_rate
