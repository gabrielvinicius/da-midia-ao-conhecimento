"""Helpers e registro para dependências de transcrição (provedores de ASR e repo).
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict

from src.media_processing.infrastructure.transcription.transcription_repository import (
    TranscriptionRepository,
)

logger = logging.getLogger(__name__)

_SPEECH_RECOGNIZERS: Dict[str, Callable[[], Any]] = {
    "whisper": lambda: _load_whisper_recognizer(),
}


def register_speech_recognition(name: str) -> Callable[[type], type]:
    """Decorador para registrar provedores de reconhecimento de fala."""

    def _decorator(cls: type) -> type:
        _SPEECH_RECOGNIZERS[name.lower()] = cls  # type: ignore[assignment]
        return cls

    return _decorator


def create_speech_recognition_service(provider: str) -> Any:
    normalized = (provider or "whisper").lower()
    factory = _SPEECH_RECOGNIZERS.get(normalized)
    if factory is not None:
        return factory()

    logger.warning(
        "speech_recognizer.provider_not_registered provider=%s available=%s",
        provider,
        list(_SPEECH_RECOGNIZERS.keys()),
    )
    return _load_whisper_recognizer()


def _load_whisper_recognizer():
    from src.media_processing.infrastructure.transcription.speech_recognizer import (
        WhisperSpeechRecognizer,
    )

    return WhisperSpeechRecognizer()


async def get_transcription_repository(session) -> TranscriptionRepository:
    return TranscriptionRepository(session)


__all__ = [
    "register_speech_recognition",
    "create_speech_recognition_service",
    "get_transcription_repository",
]
