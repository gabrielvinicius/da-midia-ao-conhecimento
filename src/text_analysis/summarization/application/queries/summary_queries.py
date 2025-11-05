"""Query helpers for accessing summarization aggregates."""

from __future__ import annotations

from typing import Optional, Protocol
from uuid import UUID

from src.text_analysis.summarization.domain.summary import Summary


class SupportsSummaryRepository(Protocol):
    async def get_by_id(self, summary_id: UUID) -> Optional[Summary]: ...
    async def get_by_media_id(self, media_id: UUID) -> Optional[Summary]: ...


def _coerce_uuid(value: UUID | str) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


class SummaryQueries:
    """Thin queries façade wrapping the async repository implementation."""

    def __init__(self, summary_repository: SupportsSummaryRepository) -> None:
        self._repository = summary_repository

    async def get_by_id(self, summary_id: UUID | str) -> Optional[Summary]:
        return await self._repository.get_by_id(_coerce_uuid(summary_id))

    async def get_by_media_id(self, media_id: UUID | str) -> Optional[Summary]:
        return await self._repository.get_by_media_id(_coerce_uuid(media_id))


__all__ = ["SummaryQueries"]
