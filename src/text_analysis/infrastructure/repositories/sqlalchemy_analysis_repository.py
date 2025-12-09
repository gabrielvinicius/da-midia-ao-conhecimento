"""SQLAlchemy-backed repository for text analysis results."""

from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import Column, String, JSON, ForeignKey, Uuid
from sqlalchemy.future import select
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import JSONB

from src.shared.infrastructure.database.db import Base
from ..application.ports import AnalysisRepositoryPort
from ..domain import Analysis, Topic


class AnalysisORM(Base):
    __tablename__ = "text_analysis_results"

    id = Column(String, primary_key=True)
    document_id = Column(String, nullable=False)
    
    # Indexed Foreign Keys for performance and integrity
    media_id = Column(Uuid(as_uuid=True), ForeignKey("media.id"), nullable=True, index=True)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    transcription_id = Column(Uuid(as_uuid=True), ForeignKey("transcriptions.id"), nullable=True, index=True)
    
    # Using JSONB for complex nested data (sentiments, topics, diagnostics)
    payload = Column(JSONB, nullable=False)


class SqlAlchemyAnalysisRepository(AnalysisRepositoryPort):
    def __init__(self, session: Session):
        self.session = session

    def save(self, analysis: Analysis) -> str:
        # Domain entities now use UUIDs, ORM expects UUID objects for FKs, String for ID
        
        data = {
            "analysis_id": str(analysis.id),
            "document_id": str(analysis.document.id),
            "overall_sentiment": analysis.overall_sentiment.value if analysis.overall_sentiment else None,
            "sentiment_items": [s.__dict__ for s in analysis.sentiments],
            "topics": [t.__dict__ for t in analysis.topics],
            "diagnostics": analysis.diagnostics,
            "media_id": str(analysis.media_id) if analysis.media_id else None,
            "transcription_id": str(analysis.transcription_id) if analysis.transcription_id else None,
            "user_id": str(analysis.user_id) if analysis.user_id else None,
        }
        
        record = AnalysisORM(
            id=str(analysis.id), 
            document_id=str(analysis.document.id), 
            media_id=analysis.media_id,
            user_id=analysis.user_id,
            transcription_id=analysis.transcription_id,
            payload=data
        )
        self.session.merge(record)
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return str(analysis.id)

    def get(self, analysis_id: str) -> Optional[Analysis]:
        stmt = select(AnalysisORM).where(AnalysisORM.id == analysis_id)
        record = self.session.execute(stmt).scalar_one_or_none()
        if not record:
            return None
        payload = record.payload or {}
        return self._payload_to_analysis(payload)

    def get_by_media_id(self, media_id: str) -> Optional[Analysis]:
        # Query using the indexed column
        try:
            media_uuid = uuid.UUID(media_id)
        except ValueError:
            return None

        stmt = select(AnalysisORM).where(AnalysisORM.media_id == media_uuid)
        record = self.session.execute(stmt).first()
        if not record:
            return None
        return self._payload_to_analysis(record[0].payload)

    def list_topics(self, analysis_id: str) -> List[Topic]:
        analysis = self.get(analysis_id)
        return analysis.topics if analysis else []

    def _payload_to_analysis(self, payload: dict) -> Analysis:
        from ..domain import Document, Analysis as AnalysisEntity, Sentiment, SentimentLabel, TextChunk, Topic

        doc_id = uuid.UUID(str(payload.get("document_id"))) if payload.get("document_id") else uuid.uuid4()
        doc = Document(id=doc_id, text="")
        
        analysis_id = uuid.UUID(str(payload.get("analysis_id"))) if payload.get("analysis_id") else uuid.uuid4()
        
        media_id = uuid.UUID(str(payload.get("media_id"))) if payload.get("media_id") else None
        transcription_id = uuid.UUID(str(payload.get("transcription_id"))) if payload.get("transcription_id") else None
        user_id = uuid.UUID(str(payload.get("user_id"))) if payload.get("user_id") else None

        analysis = AnalysisEntity(
            id=analysis_id,
            document=doc,
            media_id=media_id,
            transcription_id=transcription_id,
            user_id=user_id,
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
