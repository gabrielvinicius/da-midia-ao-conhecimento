"""Cache-backed state manager for transcriptions."""
from __future__ import annotations

from typing import Any, Optional


class TranscriptionStateManagerImpl:
    def __init__(self, cache_service: Any) -> None:
        self._cache = cache_service

    async def get(self, transcription_id: str) -> Optional[str]:
        getter = getattr(self._cache, "get", None)
        if callable(getter):
            return await getter(transcription_id)
        return None

    async def set(self, transcription_id: str, value: str) -> None:
        setter = getattr(self._cache, "set", None)
        if callable(setter):
            await setter(transcription_id, value)
