"""Async SQLAlchemy-backed repository for text analysis results."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.application.utils.serialization import to_json_serializable
from src.text_analysis.application.ports.repository import AnalysisRepositoryPort
from src.text_analysis.domain import Analysis, Topic
from src.text_analysis.infrastructure.persistence.models import AnalysisModel


class SqlAlchemyAnalysisRepository(AnalysisRepositoryPort):
    CURRENT_SCHEMA_VERSION = 2 # Increment when structure changes

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, analysis: Analysis) -> str:
        payload = {
            "schema_version": self.CURRENT_SCHEMA_VERSION, # Versioning for Level 6.0
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
            "summary": analysis.summary,
        }

        # Convert to serializable format (handle numpy arrays, etc.)
        serializable_payload = to_json_serializable(payload)

        record = AnalysisModel(
            id=str(analysis.id),
            document_id=str(analysis.document.id),
            media_id=analysis.media_id,
            user_id=analysis.user_id,
            transcription_id=analysis.transcription_id,
            payload=serializable_payload,
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
        
        # Level 6.0: Automated Schema Evolution on Read
        version = payload.get("schema_version", 1)
        if version < self.CURRENT_SCHEMA_VERSION:
            payload = self._upcast_payload(payload, from_version=version)
            # Optional: trigger background update to migrate DB record permanently
            
        return self._payload_to_analysis(payload)

    def _upcast_payload(self, payload: dict, from_version: int) -> dict:
        """Transforms legacy data formats into the current version format."""
        updated = payload.copy()
        
        if from_version == 1:
            # Example: In V1 topics might have been a simple list of strings
            # In V2 they are objects with keywords and summaries.
            if "topics" in updated and updated["topics"] and isinstance(updated["topics"][0], str):
                updated["topics"] = [{"title": t, "keywords": [t], "summary": ""} for t in updated["topics"]]
            updated["schema_version"] = 2
            
        # Add future migrations here: if from_version == 2: ...
        return updated

    async def update_summary(self, analysis_id: str, new_summary: str) -> bool:
        """Updates the summary with a human-corrected version."""
        stmt = select(AnalysisModel).where(AnalysisModel.id == analysis_id)
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        if not record:
            return False
            
        # Store original summary in diagnostics if not already there
        if "original_ai_summary" not in record.payload.get("diagnostics", {}):
            record.payload.setdefault("diagnostics", {})["original_ai_summary"] = record.payload.get("summary")
            
        record.payload["summary"] = new_summary
        record.payload["human_corrected"] = True
        
        # Mark record as modified for SQLAlchemy to detect change in JSONB
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(record, "payload")
        
        await self.session.commit()
        return True

    async def get_by_media_id(self, media_id: str) -> Optional[Analysis]:
        try:
            media_uuid = uuid.UUID(media_id)
        except ValueError:
            return None

        # Level 7.1 Fix: Handle multiple analysis results (legacy dupes)
        # Order by created_at DESC to get the latest one
        stmt = (
            select(AnalysisModel)
            .where(AnalysisModel.media_id == media_uuid)
            .order_by(AnalysisModel.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        
        if not record:
            return None
        payload = record.payload or {}
        
        # Level 6.0: Automated Schema Evolution on Read
        version = payload.get("schema_version", 1)
        if version < self.CURRENT_SCHEMA_VERSION:
            payload = self._upcast_payload(payload, from_version=version)
            
        return self._payload_to_analysis(payload)

    async def list_topics(self, analysis_id: str) -> list[Topic]:
        analysis = await self.get(analysis_id)
        return analysis.topics if analysis else []

    async def delete_by_media_id(self, media_id: uuid.UUID) -> None:
        """Deletes all analysis results associated with a media ID."""
        stmt = select(AnalysisModel).where(AnalysisModel.media_id == media_id)
        result = await self.session.execute(stmt)
        for record in result.scalars().all():
            await self.session.delete(record)
        await self.session.commit()

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

        analysis.summary = payload.get("summary")
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

