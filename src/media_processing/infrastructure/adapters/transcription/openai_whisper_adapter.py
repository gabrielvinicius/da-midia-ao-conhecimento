from __future__ import annotations

import asyncio
from typing import Any, Dict

import whisper

from src.media_processing.application.ports import SpeechRecognizer


class OpenAIWhisperTranscriber(SpeechRecognizer):
    """Adapter para o modelo Whisper oficial (biblioteca openai-whisper)."""

    def __init__(self, model_size: str = "base", device: str | None = None, **kwargs: Any) -> None:
        # load_model escolhe automaticamente CPU/GPU se device não for informado
        self._model = whisper.load_model(model_size, device=device, **kwargs)

    def _transcribe_sync(self, path: str, language: str | None):
        # language=None ativa detecção automática do whisper
        result = self._model.transcribe(path, language=language)
        return result

    async def transcribe(self, path: str, language: str = "auto") -> Dict[str, Any]:
        lang = None if not language or language.lower() == "auto" else language
        result = await asyncio.to_thread(self._transcribe_sync, path, lang)

        segments = result.get("segments") or []
        return {
            "text": result.get("text", "").strip(),
            "language": result.get("language", lang),
            "provider": "openai-whisper",
            "segments": [
                {
                    "start": seg.get("start"),
                    "end": seg.get("end"),
                    "text": seg.get("text"),
                    "confidence": seg.get("avg_logprob"),
                }
                for seg in segments
            ],
            "duration": result.get("duration"),
        }


__all__ = ["OpenAIWhisperTranscriber"]
