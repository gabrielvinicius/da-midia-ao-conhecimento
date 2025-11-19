"""SQLAlchemy repository for :class:`SummaryAggregate`."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.text_analysis.summarization.domain.model import SummaryAggregate
from src.media_processing.transcription.domain.transcription import Transcription as TranscriptionEntity

from .summary_entity import SummaryEntity
from .summary_mapper import SummaryMapper


class SummarizationRepository:
    def __init__(self, db, mapper: Optional[SummaryMapper] = None) -> None:
        self.db = db
        self._mapper = mapper or SummaryMapper()

    async def get_by_id(self, summary_id: UUID) -> Optional[SummaryAggregate]:
        # Use async method if db is an async session
        if isinstance(self.db, AsyncSession):
            result = await self.db.execute(select(SummaryEntity).where(SummaryEntity.id == summary_id))
            entity = result.scalar_one_or_none()
            if entity is None:
                return None
            return self._mapper.to_domain(entity)
        else:
            # Fallback to sync method
            return self.get_by_id_sync(summary_id)

    async def get_by_media_id(self, media_id: UUID) -> Optional[SummaryAggregate]:
        # Use async method if db is an async session
        if isinstance(self.db, AsyncSession):
            stmt = (
                select(SummaryEntity)
                .join(TranscriptionEntity, SummaryEntity.transcription_id == TranscriptionEntity.id)
                .where(TranscriptionEntity.media_id == media_id)
            )
            result = await self.db.execute(stmt)
            entity = result.scalar_one_or_none()
            if entity is None:
                return None
            return self._mapper.to_domain(entity)
        else:
            # Fallback to sync method
            return self.get_by_media_id_sync(media_id)

    def get_by_id_sync(self, summary_id: UUID) -> Optional[SummaryAggregate]:
        # Use sync method - this should only be called with sync session
        stmt = select(SummaryEntity).where(SummaryEntity.id == summary_id)
        result = self.db.execute(stmt)
        entity = result.scalar_one_or_none()
        if entity is None:
            return None
        return self._mapper.to_domain(entity)

    def get_by_transcription_id_sync(self, transcription_id: UUID) -> Optional[SummaryAggregate]:
        # Use sync method - this should only be called with sync session
        stmt = select(SummaryEntity).where(SummaryEntity.transcription_id == transcription_id)
        result = self.db.execute(stmt)
        entity = result.scalar_one_or_none()
        if entity is None:
            return None
        return self._mapper.to_domain(entity)

    def get_by_media_id_sync(self, media_id: UUID) -> Optional[SummaryAggregate]:
        # Use sync method - this should only be called with sync session
        stmt = (
            select(SummaryEntity)
            .join(TranscriptionEntity, SummaryEntity.transcription_id == TranscriptionEntity.id)
            .where(TranscriptionEntity.media_id == media_id)
        )
        result = self.db.execute(stmt)
        entity = result.scalar_one_or_none()
        if entity is None:
            return None
        return self._mapper.to_domain(entity)

    async def get_by_transcription_id(self, transcription_id: UUID) -> Optional[SummaryAggregate]:
        if isinstance(self.db, AsyncSession):
            result = await self.db.execute(
                select(SummaryEntity).where(SummaryEntity.transcription_id == transcription_id)
            )
            entity = result.scalar_one_or_none()
            if entity is None:
                return None
            return self._mapper.to_domain(entity)
        return self.get_by_transcription_id_sync(transcription_id)

    async def add(self, summary: SummaryAggregate) -> SummaryAggregate:
        # Use async method if db is an async session
        if isinstance(self.db, AsyncSession):
            entity = self._mapper.to_entity(summary)
            self.db.add(entity)
            await self.db.flush()
            return self._mapper.merge_transient_data(
                self._mapper.to_domain(entity),
                summary,
            )
        else:
            # Fallback to sync method
            return self.add_sync(summary)

    async def update(self, summary: SummaryAggregate) -> SummaryAggregate:
        # Use async method if db is an async session
        if isinstance(self.db, AsyncSession):
            merged = await self.db.merge(self._mapper.to_entity(summary))
            await self.db.flush()
            return self._mapper.merge_transient_data(
                self._mapper.to_domain(merged),
                summary,
            )
        else:
            # Fallback to sync method
            return self.update_sync(summary)

    def add_sync(self, summary: SummaryAggregate) -> SummaryAggregate:
        # Use sync method - this should only be called with sync session
        entity = self._mapper.to_entity(summary)
        self.db.add(entity)
        self.db.flush()
        return self._mapper.merge_transient_data(
            self._mapper.to_domain(entity),
            summary,
        )

    def update_sync(self, summary: SummaryAggregate) -> SummaryAggregate:
        # Use sync method - this should only be called with sync session
        merged = self.db.merge(self._mapper.to_entity(summary))
        self.db.flush()
        return self._mapper.merge_transient_data(
            self._mapper.to_domain(merged),
            summary,
        )

    async def save(self, summary: SummaryAggregate) -> SummaryAggregate:
        return await self.update(summary)

    def save_sync(self, summary: SummaryAggregate) -> SummaryAggregate:
        return self.update_sync(summary)

    async def delete_by_media_id(self, media_id: UUID) -> None:
        if isinstance(self.db, AsyncSession):
            stmt = (
                select(SummaryEntity)
                .join(TranscriptionEntity, SummaryEntity.transcription_id == TranscriptionEntity.id)
                .where(TranscriptionEntity.media_id == media_id)
            )
            result = await self.db.execute(stmt)
            for entity in result.scalars().all():
                await self.db.delete(entity)
            await self.db.flush()
        else:
            self.delete_by_media_id_sync(media_id)

    def delete_by_media_id_sync(self, media_id: UUID) -> None:
        stmt = (
            select(SummaryEntity)
            .join(TranscriptionEntity, SummaryEntity.transcription_id == TranscriptionEntity.id)
            .where(TranscriptionEntity.media_id == media_id)
        )
        result = self.db.execute(stmt)
        for entity in result.scalars().all():
            self.db.delete(entity)
        self.db.flush()
