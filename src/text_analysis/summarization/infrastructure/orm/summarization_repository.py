"""SQLAlchemy repository for :class:`SummaryAggregate`."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.summarization.domain.model import SummaryAggregate

from .summary_entity import SummaryEntity
from .summary_mapper import SummaryMapper


class SummarizationRepository:
    def __init__(self, db: AsyncSession, mapper: Optional[SummaryMapper] = None) -> None:
        self.db = db
        self._mapper = mapper or SummaryMapper()

    async def get_by_id(self, summary_id: UUID) -> Optional[SummaryAggregate]:
        result = await self.db.execute(select(SummaryEntity).where(SummaryEntity.id == summary_id))
        entity = result.scalar_one_or_none()
        if entity is None:
            return None
        return self._mapper.to_domain(entity)

    async def get_by_media_id(self, media_id: UUID) -> Optional[SummaryAggregate]:
        result = await self.db.execute(select(SummaryEntity).where(SummaryEntity.media_id == media_id))
        entity = result.scalar_one_or_none()
        if entity is None:
            return None
        return self._mapper.to_domain(entity)

    async def add(self, summary: SummaryAggregate) -> SummaryAggregate:
        entity = self._mapper.to_entity(summary)
        self.db.add(entity)
        await self.db.flush()
        return self._mapper.merge_transient_data(
            self._mapper.to_domain(entity),
            summary,
        )

    async def update(self, summary: SummaryAggregate) -> SummaryAggregate:
        merged = await self.db.merge(self._mapper.to_entity(summary))
        await self.db.flush()
        return self._mapper.merge_transient_data(
            self._mapper.to_domain(merged),
            summary,
        )

    async def save(self, summary: SummaryAggregate) -> SummaryAggregate:
        return await self.update(summary)

    async def delete_by_media_id(self, media_id: UUID) -> None:
        result = await self.db.execute(select(SummaryEntity).where(SummaryEntity.media_id == media_id))
        entity = result.scalar_one_or_none()
        if entity is not None:
            await self.db.delete(entity)
            await self.db.flush()
