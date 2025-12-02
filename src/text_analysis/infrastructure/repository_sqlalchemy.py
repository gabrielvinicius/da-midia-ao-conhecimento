"""SQLAlchemy-backed repository for text analysis results."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import Column, String, JSON, cast
from sqlalchemy.future import select
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import JSONB

from src.shared.infrastructure.database import Base
from ..application.ports import AnalysisRepositoryPort
from ..domain import Analysis, Topic


class AnalysisORM(Base):
    __tablename__ = "text_analysis_results"

    id = Column(String, primary_key=True)
    document_id = Column(String, nullable=False)
    # Using JSONB for better query performance on Postgres
    payload = Column(JSONB, nullable=False)


class SqlAlchemyAnalysisRepository(AnalysisRepositoryPort):
    def __init__(self, session: Session):
        self.session = session

    def save(self, analysis: Analysis) -> str:
        data = {
            "analysis_id": analysis.id,
            "document_id": analysis.document.id,
            "overall_sentiment": analysis.overall_sentiment.value if analysis.overall_sentiment else None,
            "sentiment_items": [s.__dict__ for s in analysis.sentiments],
            "topics": [t.__dict__ for t in analysis.topics],
            "diagnostics": analysis.diagnostics,
            "media_id": analysis.media_id,
            "transcription_id": analysis.transcription_id,
            "user_id": analysis.user_id,
        }
        record = AnalysisORM(id=analysis.id, document_id=analysis.document.id, payload=data)
        self.session.merge(record)
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return analysis.id

    def get(self, analysis_id: str) -> Optional[Analysis]:
        stmt = select(AnalysisORM).where(AnalysisORM.id == analysis_id)
        record = self.session.execute(stmt).scalar_one_or_none()
        if not record:
            return None
        payload = record.payload or {}
        return self._payload_to_analysis(payload)

    def get_by_media_id(self, media_id: str) -> Optional[Analysis]:
        # Query into the JSONB payload
        # Note: We cast media_id to string to ensure type matching in JSON
        stmt = select(AnalysisORM).where(
            AnalysisORM.payload["media_id"].astext == str(media_id)
        )
        # Order by something? Maybe implicit insertion order or create a created_at column?
        # For now, take the first one found (assuming one analysis per media usually)
        record = self.session.execute(stmt).first()
        if not record:
            return None
        # record is a Row (AnalysisORM,), so record[0] is the entity
        return self._payload_to_analysis(record[0].payload)

    def list_topics(self, analysis_id: str) -> List[Topic]:
        analysis = self.get(analysis_id)
        return analysis.topics if analysis else []

    def _payload_to_analysis(self, payload: dict) -> Analysis:
        from ..domain import Document, Analysis as AnalysisEntity, Sentiment, SentimentLabel, TextChunk, Topic

        doc = Document(id=payload.get("document_id", ""), text="")
        analysis = AnalysisEntity(
            id=payload.get("analysis_id", ""),
            document=doc,
            media_id=payload.get("media_id"),
            transcription_id=payload.get("transcription_id"),
            user_id=payload.get("user_id"),
        )

        chunks = []
        for item in payload.get("sentiment_items", []):
            chunks.append(TextChunk(id=item.get("chunk_id", ""), text=item.get("text", "")))
        analysis.chunks = chunks

        sentiments = []
        for item in payload.get("sentiment_items", []):
            sentiments.append(
                Sentiment(
                    chunk_id=item.get("chunk_id", ""),
                    label=SentimentLabel(item.get("label", "NEU")),
                    score=item.get("score", 0.0),
                )
            )
        analysis.sentiments = sentiments

        topics = []
        for t in payload.get("topics", []):
            topics.append(
                Topic(
                    topic_id=t.get("topic_id", 0),
                    keywords=t.get("keywords", []),
                    snippets=t.get("representative_snippets", t.get("snippets", [])),
                    title=t.get("title"),
                    summary_md=t.get("summary_md"),
                    size=t.get("size", 0),
                    diagnostics=t.get("diagnostics"),
                )
            )
        analysis.topics = topics
        analysis.overall_sentiment = SentimentLabel(payload.get("overall_sentiment", "NEU"))
        analysis.diagnostics = payload.get("diagnostics", {})
        return analysis