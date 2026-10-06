from __future__ import annotations

import asyncio
from typing import Any, Dict

from src.media_processing.application.ports import SpeechRecognizer
from src.shared.infrastructure.config.settings import settings


class OpenAIWhisperTranscriber(SpeechRecognizer):
    """Adapter para o modelo Whisper oficial (biblioteca openai-whisper)."""

    # No openai-whisper, o large-v3-turbo se chama "turbo".
    _ALIASES = {"large-v3-turbo": "turbo"}

    def __init__(self, model_size: str | None = None, device: str | None = None, **kwargs: Any) -> None:
        # Antes o padrão era "base", bem menos preciso que o modelo documentado.
        requested = model_size or settings.whisper_model
        self.model_size = self._ALIASES.get(requested, requested)
        self.model_label = f"openai-whisper {self.model_size}"
        self.device = device or settings.resolved_device
        self.kwargs = kwargs
        self._model = None
        self._initialized = False

    def _get_model(self):
        if not self._initialized:
            import whisper
            self._model = whisper.load_model(self.model_size, device=self.device, **self.kwargs)
            self._initialized = True
        return self._model

    def _transcribe_sync(self, path: str, language: str | None):
        # language=None ativa detecção automática do whisper
        model = self._get_model()
        result = model.transcribe(path, language=language)
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
