"""Domain entities for the text_analysis bounded context."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
from uuid import UUID, uuid4

from src.shared.domain.base_entity import Entity, AggregateRoot
from .errors import EmptyTextError, InvalidSegmentError
from .value_objects import Sentiment, SentimentLabel, TextChunk, Topic


def _validate_text(text: str) -> str:
    if not text or not text.strip():
        raise EmptyTextError("Text cannot be empty.")
    return text


@dataclass(kw_only=True, slots=True)
class Document(Entity):
    text: str
    segments: Optional[list[dict]] = None

    @classmethod
    def from_payload(cls, text: str, segments: Optional[list[dict]] = None) -> "Document":
        _validate_text(text)
        if segments:
            for segment in segments:
                if not isinstance(segment, dict) or "text" not in segment:
                    raise InvalidSegmentError("Segment must contain 'text'.")
        return cls(id=uuid4(), text=text, segments=segments)


@dataclass(kw_only=True, slots=True)
class Analysis(AggregateRoot):
    document: Document
    media_id: Optional[UUID] = None
    transcription_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    chunks: List[TextChunk] = field(default_factory=list)
    sentiments: List[Sentiment] = field(default_factory=list)
    overall_sentiment: Optional[SentimentLabel] = None
    topics: List[Topic] = field(default_factory=list)
    diagnostics: dict = field(default_factory=dict)

    @classmethod
    def new(
        cls, 
        document: Document, 
        media_id: Optional[UUID] = None, 
        transcription_id: Optional[UUID] = None, 
        user_id: Optional[UUID] = None
    ) -> "Analysis":
        return cls(
            id=uuid4(), 
            document=document, 
            media_id=media_id, 
            transcription_id=transcription_id, 
            user_id=user_id
        )

