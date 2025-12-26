"""Async SQLAlchemy-backed repository for text analysis results."""

from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.text_analysis.application.ports.repository import AnalysisRepositoryPort
from src.text_analysis.domain import Analysis, Topic
from src.text_analysis.infrastructure.persistence.models import AnalysisModel


class SqlAlchemyAnalysisRepository(AnalysisRepositoryPort):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, analysis: Analysis) -> str:
        payload = {
            "analysis_id": str(analysis.id),
            "document_id": str(analysis.document.id),
            "overall_sentiment": (
                analysis.overall_sentiment.value if analysis.overall_sentiment else None
            ),
            "sentiment_items": [s.__dict__ for s in analysis.sentiments],
            "topics": [t.__dict__ for t in analysis.topics],
            "diagnostics": analysis.diagnostics,
            "media_id": str(analysis.media_id) if analysis.media_id else None,
            "transcription_id": (
                str(analysis.transcription_id) if analysis.transcription_id else None
            ),
            "user_id": str(analysis.user_id) if analysis.user_id else None,
        }

        record = AnalysisModel(
            id=str(analysis.id),
            document_id=str(analysis.document.id),
            media_id=analysis.media_id,
            user_id=analysis.user_id,
            transcription_id=analysis.transcription_id,
            payload=payload,
        )
        await self.session.merge(record)
        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        return str(analysis.id)

    async def get(self, analysis_id: str) -> Optional[Analysis]:
        stmt = select(AnalysisModel).where(AnalysisModel.id == analysis_id)
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        if not record:
            return None
        payload = record.payload or {}
        return self._payload_to_analysis(payload)

    async def get_by_media_id(self, media_id: str) -> Optional[Analysis]:
        try:
            media_uuid = uuid.UUID(media_id)
        except ValueError:
            return None

        stmt = select(AnalysisModel).where(AnalysisModel.media_id == media_uuid)
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        if not record:
            return None
        payload = record.payload or {}
        return self._payload_to_analysis(payload)

    async def list_topics(self, analysis_id: str) -> List[Topic]:
        analysis = await self.get(analysis_id)
        return analysis.topics if analysis else []

    def _payload_to_analysis(self, payload: dict) -> Analysis:
        from src.text_analysis.domain import Analysis as AnalysisEntity
        from src.text_analysis.domain import Document, Sentiment, SentimentLabel, TextChunk, Topic

        doc_id = (
            uuid.UUID(str(payload.get("document_id")))
            if payload.get("document_id")
            else uuid.uuid4()
        )
        doc = Document(id=doc_id, text="")

        analysis_id = (
            uuid.UUID(str(payload.get("analysis_id")))
            if payload.get("analysis_id")
            else uuid.uuid4()
        )

        media_id = (
            uuid.UUID(str(payload.get("media_id")))
            if payload.get("media_id")
            else None
        )
        transcription_id = (
            uuid.UUID(str(payload.get("transcription_id")))
            if payload.get("transcription_id")
            else None
        )
        user_id = (
            uuid.UUID(str(payload.get("user_id")))
            if payload.get("user_id")
            else None
        )

        analysis = AnalysisEntity(
            id=analysis_id,
            document=doc,
            media_id=media_id,
            transcription_id=transcription_id,
            user_id=user_id,
        )

        sentiments = []
        for raw in payload.get("sentiment_items") or []:
            try:
                label = SentimentLabel[str(raw.get("label", "NEUTRAL")).upper()]
            except Exception:
                label = SentimentLabel.NEUTRAL
            sentiments.append(
                Sentiment(
                    chunk_id=str(raw.get("chunk_id", "")),
                    label=label,
                    score=float(raw.get("score", 0.0)),
                    text=str(raw.get("text", "")),
                )
            )
        analysis.sentiments = sentiments

        topics = []
        for raw in payload.get("topics") or []:
            topics.append(
                Topic(
                    id=str(raw.get("id", "")),
                    title=raw.get("title"),
                    keywords=list(raw.get("keywords", []) or []),
                    snippets=list(raw.get("snippets", []) or []),
                    summary=raw.get("summary"),
                    diagnostics=raw.get("diagnostics") or {},
                )
            )
        analysis.topics = topics

        analysis.diagnostics = payload.get("diagnostics") or {}
        overall = payload.get("overall_sentiment")
        if overall:
            try:
                analysis.overall_sentiment = SentimentLabel[str(overall).upper()]
            except Exception:
                analysis.overall_sentiment = None

        # Chunks são opcionais no payload atual
        chunks = []
        for raw in payload.get("chunks") or []:
            chunks.append(
                TextChunk(
                    id=str(raw.get("id", "")),
                    text=str(raw.get("text", "")),
                    start=int(raw.get("start", 0)),
                    end=int(raw.get("end", 0)),
                )
            )
        analysis.chunks = chunks

        return analysis


__all__ = ["SqlAlchemyAnalysisRepository"]

