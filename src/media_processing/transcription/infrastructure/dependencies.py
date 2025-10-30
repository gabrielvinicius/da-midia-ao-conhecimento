"""
Helpers e registro para dependências de transcrição (provedores de ASR e repo).
"""
from __future__ import annotations

from typing import Any, Callable, Dict

from src.media_processing.transcription.infrastructure.speech_recognizer import WhisperSpeechRecognizer
from src.media_processing.transcription.infrastructure.transcription_repository import TranscriptionRepository

_SPEECH_RECOGNIZERS: Dict[str, Callable[[], Any]] = {}


def register_speech_recognition(name: str) -> Callable[[type], type]:
    """Decorador para registrar provedores de reconhecimento de fala."""

    def _decorator(cls: type) -> type:
        _SPEECH_RECOGNIZERS[name] = cls  # type: ignore[assignment]
        return cls

    return _decorator


def create_speech_recognition_service(provider: str) -> Any:
    factory = _SPEECH_RECOGNIZERS.get(provider)
    if factory is not None:
        return factory()
    # Fallback padrão
    return WhisperSpeechRecognizer()


async def get_transcription_repository(session) -> TranscriptionRepository:
    return TranscriptionRepository(session)


__all__ = [
    "register_speech_recognition",
    "create_speech_recognition_service",
    "get_transcription_repository",
]
