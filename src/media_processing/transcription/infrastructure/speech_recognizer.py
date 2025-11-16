"""Whisper speech recognition backed by the openai-whisper package."""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Dict, Optional

import numpy as np
import whisper

logger = logging.getLogger(__name__)


class WhisperSpeechRecognizer:
    """Real Whisper-based recognizer (no placeholders)."""

    def __init__(
        self,
        model_name: str = "base",
        device: Optional[str] = None,
        sample_rate: int = 16000,
    ) -> None:
        import torch

        self.sample_rate = sample_rate
        resolved_device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        download_root = os.getenv("WHISPER_CACHE_DIR", "/app/.cache/whisper")
        os.makedirs(download_root, exist_ok=True)
        self.model = whisper.load_model(
            model_name,
            device=resolved_device,
            download_root=download_root,
        )

    @property
    def provider_name(self) -> str:
        return "whisper"

    async def transcribe(self, file: bytes, language: str = "en") -> Dict[str, object]:
        logger.debug(
            "whisper.transcribe.start",
            language=language,
            payload_size=len(file),
        )
        audio = await self._decode_audio_bytes(file)
        loop = asyncio.get_running_loop()

        def _run():
            result = self.model.transcribe(audio, language=language)
            return {
                "text": result.get("text", "").strip(),
                "segments": result.get("segments"),
                "language": result.get("language", language),
                "provider": self.provider_name,
            }

        return await loop.run_in_executor(None, _run)

    async def _decode_audio_bytes(self, file_bytes: bytes) -> np.ndarray:
        """Use FFmpeg to convert any media into mono PCM float array."""
        command = [
            "ffmpeg",
            "-i",
            "pipe:0",
            "-f",
            "s16le",
            "-ac",
            "1",
            "-ar",
            str(self.sample_rate),
            "-loglevel",
            "error",
            "-hide_banner",
            "pipe:1",
        ]

        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate(input=file_bytes)
        await process.wait()

        if process.returncode != 0:
            message = stderr.decode().strip() if stderr else f"FFmpeg error {process.returncode}"
            logger.error("whisper.audio_decode_failed", extra={"error": message})
            raise RuntimeError(f"Audio decoding failed: {message}")

        audio_array = np.frombuffer(stdout, dtype=np.int16).astype(np.float32)
        audio_array /= np.abs(audio_array).max() + 1e-9
        return audio_array
