from __future__ import annotations

from typing import Any

from src.shared.infrastructure.config.settings import settings

class FastWhisperTranscriber(SpeechRecognizer):
    """Adapter para o Faster-Whisper (CTranslate2)."""

    def __init__(
        self,
        model_size: str = "medium",
        device: str | None = None,
        compute_type: str | None = None,
        **kwargs: Any,
    ) -> None:
        self.model_size = model_size
        self.device = device or settings.resolved_device
        self.compute_type = compute_type or settings.ai_compute_type
        if self.compute_type == "default":
            # For faster-whisper, default depends on device
            self.compute_type = "float16" if self.device == "cuda" else "int8"
        
        self.kwargs = kwargs
        self._model = None
        self._initialized = False

    def _get_model(self):
        if not self._initialized:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                **self.kwargs,
            )
            self._initialized = True
        return self._model

    async def transcribe(self, path: str, language: str = "auto"):
        model = self._get_model()
        segments, info = model.transcribe(path, language=language)
        text = " ".join([seg.text for seg in segments])
        return {
            "text": text,
            "language": info.language if hasattr(info, "language") else language,
            "provider": "fastwhisper",
            "segments": [
                {
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text,
                    "confidence": seg.avg_log_prob,
                }
                for seg in segments
            ],
            "duration": info.duration if hasattr(info, "duration") else None,
        }


__all__ = ["FastWhisperTranscriber"]
