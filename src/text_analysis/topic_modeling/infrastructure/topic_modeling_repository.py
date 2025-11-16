# src/topic_modeling/infrastructure/topic_modeling_repository.py
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.text_analysis.topic_modeling.domain.topic_modeling import TopicModelingResult


class TopicModelingRepository:
    """SQLAlchemy implementation of the topic modeling repository."""

    def __init__(self, db):
        self.db = db

    async def get_by_id(self, result_id: UUID) -> Optional[TopicModelingResult]:
        result = await self.db.execute(select(TopicModelingResult).where(TopicModelingResult.id == result_id))
        return result.scalar_one_or_none()

    async def add(self, result: TopicModelingResult) -> None:
        self.db.add(result)
        await self.db.flush()

    async def update(self, result: TopicModelingResult) -> None:
        # For SQLAlchemy, just adding to session and flushing is usually enough for updates
        # if the object is already tracked or has a primary key.
        await self.db.flush()

    async def get_by_media_id(self, media_id: UUID) -> Optional[TopicModelingResult]:
        result = await self.db.execute(select(TopicModelingResult).where(TopicModelingResult.media_id == media_id))
        return result.scalar_one_or_none()

    def get_by_id_sync(self, result_id: UUID) -> Optional[TopicModelingResult]:
        stmt = select(TopicModelingResult).where(TopicModelingResult.id == result_id)
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()

    def get_by_media_id_sync(self, media_id: UUID) -> Optional[TopicModelingResult]:
        stmt = select(TopicModelingResult).where(TopicModelingResult.media_id == media_id)
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()

    def get_by_transcription_id_sync(self, transcription_id: UUID) -> Optional[TopicModelingResult]:
        stmt = select(TopicModelingResult).where(TopicModelingResult.transcription_id == transcription_id)
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()

    def add_sync(self, result: TopicModelingResult) -> TopicModelingResult:
        self.db.add(result)
        self.db.flush()
        return result

    def update_sync(self, result: TopicModelingResult) -> TopicModelingResult:
        self.db.flush()
        return result