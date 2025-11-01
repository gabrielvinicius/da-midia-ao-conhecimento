"""Validation helpers for transcription requests."""
from __future__ import annotations

from typing import Iterable


class TranscriptionValidator:
    def __init__(
        self,
        *,
        min_audio_size: int = 100,
        max_audio_size: int = 1_000_000,
        supported_languages: Iterable[str] | None = None,
    ) -> None:
        self._min = min_audio_size
        self._max = max_audio_size
        self._languages = {lang.lower() for lang in (supported_languages or {"en"})}

    def validate(self, audio: bytes, language: str) -> None:
        if audio is None:
            raise ValueError("Audio payload cannot be null")
        size = len(audio)
        if size < self._min:
            raise ValueError("Audio payload too small")
        if size > self._max:
            raise ValueError("Audio payload too large")
        if language and language.lower() not in self._languages:
            raise ValueError(f"Unsupported language: {language}")
