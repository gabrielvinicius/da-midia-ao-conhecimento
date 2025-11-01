"""State manager for summarization results using an async cache."""
from __future__ import annotations

from typing import Any, Optional


class SummaryStateManagerImpl:
    """Lightweight cache-backed state manager used in tests."""

    def __init__(self, cache_service: Any) -> None:
        self._cache = cache_service

    async def get(self, summary_id: str) -> Optional[str]:
        if summary_id is None:
            return None
        if hasattr(self._cache, "get"):
            return await self._cache.get(summary_id)
        return None

    async def set(self, summary_id: str, value: str) -> None:
        if summary_id is None or value is None:
            return
        setter = getattr(self._cache, "set", None)
        if callable(setter):
            await setter(summary_id, value)

