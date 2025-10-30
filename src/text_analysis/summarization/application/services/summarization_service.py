"""High-level summarization orchestration service."""
from __future__ import annotations

import time
from typing import Dict, Mapping, Optional
from uuid import UUID


class SummarizationService:
    """Coordinates summarizer provider, validation, metrics and caching."""

    def __init__(
        self,
        *,
        summarizer_provider,
        validator,
        metrics_service,
        state_manager,
    ) -> None:
        self._provider = summarizer_provider
        self._validator = validator
        self._metrics = metrics_service
        self._state = state_manager

    async def summarize(self, text: str, *, summary_id: Optional[UUID] = None) -> str:
        """Summarize the provided text, optionally using cache when id available."""

        self._validator.validate(text)
        cache_key = str(summary_id) if summary_id is not None else None
        if cache_key:
            cached = await self._state.get(cache_key)
            if cached:
                return cached

        start = time.monotonic()
        try:
            result = await self._provider.summarize(text)
            success = True
        except Exception:
            success = False
            raise
        finally:
            if self._metrics is not None:
                self._metrics.record_summary(
                    success=success,
                    duration=time.monotonic() - start,
                )

        if cache_key:
            await self._state.set(cache_key, result)
        return result

    async def batch_summarize(self, entries: Mapping[UUID, str]) -> Dict[UUID, str]:
        """Summarize a batch of texts sequentially."""

        summaries: Dict[UUID, str] = {}
        for key, text in entries.items():
            summaries[key] = await self.summarize(text, summary_id=key)
        return summaries

