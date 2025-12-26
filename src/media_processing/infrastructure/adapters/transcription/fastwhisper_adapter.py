from __future__ import annotations

from typing import Any

from faster_whisper import WhisperModel

from src.media_processing.application.ports import SpeechRecognizer


class FastWhisperTranscriber(SpeechRecognizer):
    """Adapter para o Faster-Whisper (CTranslate2)."""

    def __init__(
        self,
        model_size: str = "medium",
        device: str = "auto",
        compute_type: str = "default",
        **kwargs: Any,
    ) -> None:
        self._model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
            **kwargs,
        )

    async def transcribe(self, path: str, language: str = "auto"):
        segments, info = self._model.transcribe(path, language=language)
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
