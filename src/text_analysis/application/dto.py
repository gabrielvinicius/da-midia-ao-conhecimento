"""DTO definitions for input/output boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass(slots=True)
class SentimentItemDTO:
    chunk_id: str
    label: str
    score: float
    text: str
    start: Optional[float] = None
    end: Optional[float] = None


@dataclass(slots=True)
class TopicDTO:
    topic_id: int
    title: Optional[str]
    keywords: list[str]
    summary_md: Optional[str]
    representative_snippets: list[str]
    size: int
    diagnostics: dict


@dataclass(slots=True)
class AnalysisResultDTO:
    analysis_id: str
    document_id: str
    overall_sentiment: str
    sentiment_items: List[SentimentItemDTO]
    topics: List[TopicDTO]
    diagnostics: dict
    media_id: Optional[str] = None
    transcription_id: Optional[str] = None
    user_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "analysis_id": self.analysis_id,
            "document_id": self.document_id,
            "overall_sentiment": self.overall_sentiment,
            "sentiment_items": [item.__dict__ for item in self.sentiment_items],
            "topics": [topic.__dict__ for topic in self.topics],
            "diagnostics": self.diagnostics,
            "media_id": self.media_id,
            "transcription_id": self.transcription_id,
            "user_id": self.user_id,
        }
