"""Repository implementation for sentiment analysis aggregates."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.media_processing.transcription.domain.transcription import Transcription
from src.text_analysis.sentiment_analysis.domain.sentiment_analysis import (
    SentimentAnalysis,
    SentimentAnalysisRecord,
)


class SentimentAnalysisRepository:
    """Persist and retrieve ``SentimentAnalysis`` aggregates."""

    def __init__(self, db) -> None:
        self._db = db

    async def save(self, analysis: SentimentAnalysis) -> SentimentAnalysis:
        """Insert or update a sentiment analysis result."""
        record = await self._get_record_by_id(analysis.id)
        if record:
            record.update_from_entity(analysis)
        else:
            record = SentimentAnalysisRecord.from_entity(analysis)
            self._db.add(record)

        await self._db.flush()
        return record.to_entity()

    async def get_by_id(self, analysis_id: str) -> Optional[SentimentAnalysis]:
        record = await self._get_record_by_id(analysis_id)
        return record.to_entity() if record else None

    async def find_by_transcription_id(
        self, transcription_id: str
    ) -> Optional[SentimentAnalysis]:
        stmt = select(SentimentAnalysisRecord).where(
            SentimentAnalysisRecord.transcription_id == transcription_id
        )
        result = await self._db.execute(stmt)
        record = result.scalar_one_or_none()
        return record.to_entity() if record else None

    async def get_by_media_id(self, media_id: str) -> Optional[SentimentAnalysis]:
        stmt = (
            select(SentimentAnalysisRecord)
            .join(Transcription, SentimentAnalysisRecord.transcription_id == Transcription.id)
            .where(Transcription.media_id == media_id)
        )
        result = await self._db.execute(stmt)
        record = result.scalar_one_or_none()
        return record.to_entity() if record else None

    async def _get_record_by_id(
        self, analysis_id: str
    ) -> Optional[SentimentAnalysisRecord]:
        stmt = select(SentimentAnalysisRecord).where(
            SentimentAnalysisRecord.id == analysis_id
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    def save_sync(self, analysis: SentimentAnalysis) -> SentimentAnalysis:
        """Insert or update a sentiment analysis result."""
        record = self._get_record_by_id_sync(analysis.id)
        if record:
            record.update_from_entity(analysis)
        else:
            record = SentimentAnalysisRecord.from_entity(analysis)
            self._db.add(record)

        self._db.flush()
        return record.to_entity()

    def get_by_id_sync(self, analysis_id: str) -> Optional[SentimentAnalysis]:
        record = self._get_record_by_id_sync(analysis_id)
        return record.to_entity() if record else None

    def find_by_transcription_id_sync(
        self, transcription_id: str
    ) -> Optional[SentimentAnalysis]:
        stmt = select(SentimentAnalysisRecord).where(
            SentimentAnalysisRecord.transcription_id == transcription_id
        )
        result = self._db.execute(stmt)
        record = result.scalar_one_or_none()
        return record.to_entity() if record else None

    def get_by_media_id_sync(self, media_id: str) -> Optional[SentimentAnalysis]:
        stmt = (
            select(SentimentAnalysisRecord)
            .join(Transcription, SentimentAnalysisRecord.transcription_id == Transcription.id)
            .where(Transcription.media_id == media_id)
        )
        result = self._db.execute(stmt)
        record = result.scalar_one_or_none()
        return record.to_entity() if record else None

    def _get_record_by_id_sync(
        self, analysis_id: str
    ) -> Optional[SentimentAnalysisRecord]:
        stmt = select(SentimentAnalysisRecord).where(
            SentimentAnalysisRecord.id == analysis_id
        )
        result = self._db.execute(stmt)
        return result.scalar_one_or_none()


__all__ = ["SentimentAnalysisRepository"]
