"""Pydantic schemas exposed by the summarisation HTTP layer."""

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from src.shared.api.unified_schemas import BaseResponseSchema
from src.text_analysis.summarization.domain.model import SummaryAggregate, SummaryStatus


class SummaryResponse(BaseModel):
    """Normalised representation returned to API consumers."""

    id: str
    media_id: str
    status: SummaryStatus
    provider: Optional[str] = None
    text: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    strategy: Optional[str] = None
    bullet_points: Optional[List[str]] = None
    key_topics: Optional[List[str]] = None
    confidence_score: Optional[float] = None
    processing_time: Optional[float] = None

    @classmethod
    def from_domain(
        cls,
        summary: SummaryAggregate,
        *,
        media_id: Optional[str] = None,
    ) -> "SummaryResponse":
        """Convert the domain aggregate into a serialisable DTO."""
        bullet_points = list(summary.bullet_points) if summary.bullet_points else None
        key_topics = list(summary.key_topics) if summary.key_topics else None

        media_identifier = media_id or (
            str(summary.media_id) if getattr(summary, "media_id", None) else None
        )
        if media_identifier is None:
            raise ValueError("media_id is required to serialise a summary response")

        return cls(
            id=str(summary.id),
            media_id=media_identifier,
            status=summary.status,
            provider=summary.provider,
            text=summary.text,
            created_at=summary.created_at,
            processed_at=summary.processed_at,
            error_message=summary.error_message,
            strategy=getattr(summary, "strategy", None),
            bullet_points=bullet_points,
            key_topics=key_topics,
            confidence_score=getattr(summary, "confidence_score", None),
            processing_time=getattr(summary, "processing_time", None),
        )


class SummaryReprocessAck(BaseModel):
    """Details returned when a reprocess request is accepted for background execution."""

    media_id: UUID
    provider: str
    status: Literal["PROCESSING"] = Field(default="PROCESSING")
    task_id: Optional[str] = None


class SummaryReprocessResponse(BaseResponseSchema):
    """Envelope used when reprocessing is scheduled asynchronously."""

    reprocessing: SummaryReprocessAck
