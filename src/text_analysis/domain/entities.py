"""Domain entities for the text_analysis bounded context."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
from uuid import uuid4

from .errors import EmptyTextError, InvalidSegmentError
from .value_objects import Sentiment, SentimentLabel, TextChunk, Topic


def _validate_text(text: str) -> str:
    if not text or not text.strip():
        raise EmptyTextError("Text cannot be empty.")
    return text


@dataclass(slots=True)
class Document:
    id: str
    text: str
    segments: Optional[list[dict]] = None

    @classmethod
    def from_payload(cls, text: str, segments: Optional[list[dict]] = None) -> "Document":
        _validate_text(text)
        if segments:
            for segment in segments:
                if not isinstance(segment, dict) or "text" not in segment:
                    raise InvalidSegmentError("Segment must contain 'text'.")
        return cls(id=str(uuid4()), text=text, segments=segments)


@dataclass(slots=True)
class Analysis:
    id: str
    document: Document
    media_id: Optional[str] = None
    transcription_id: Optional[str] = None
    user_id: Optional[str] = None
    chunks: List[TextChunk] = field(default_factory=list)
    sentiments: List[Sentiment] = field(default_factory=list)
    overall_sentiment: Optional[SentimentLabel] = None
    topics: List[Topic] = field(default_factory=list)
    diagnostics: dict = field(default_factory=dict)

    @classmethod
    def new(cls, document: Document) -> "Analysis":
        return cls(id=str(uuid4()), document=document)
