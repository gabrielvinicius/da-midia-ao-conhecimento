from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.shared.application.utils.serialization import to_json_serializable

# --- Commands ---

class AnalyzeTextCommand(BaseModel):
    model_config = ConfigDict(frozen=True)
    media_id: UUID = Field(..., description="ID of the media associated with the text.")
    document_id: UUID = Field(..., description="ID of the document to analyze.")
    text_content: str = Field(..., description="The actual text content to analyze.")
    user_id: Optional[UUID] = Field(
        None,
        description="ID of the user who owns the content.",
    )
    transcription_id: Optional[UUID] = Field(
        None,
        description="ID of the transcription, if applicable.",
    )
    language: Optional[str] = Field(
        None,
        description="Language of the text content.",
    )

# --- Queries ---

class GetAnalysisQuery(BaseModel):
    model_config = ConfigDict(frozen=True)
    analysis_id: UUID = Field(..., description="ID of the text analysis result.")


class GetAnalysisByMediaIdQuery(BaseModel):
    model_config = ConfigDict(frozen=True)
    media_id: UUID = Field(
        ...,
        description="ID of the media associated with the analysis.",
    )


class ListTopicsQuery(BaseModel):
    model_config = ConfigDict(frozen=True)
    analysis_id: UUID = Field(..., description="ID of the analysis to list topics for.")

# --- Output DTOs ---

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
    summary: Optional[str]
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
    summary: Optional[str] = None

    def to_dict(self) -> dict:
        data = {
            "analysis_id": self.analysis_id,
            "document_id": self.document_id,
            "overall_sentiment": self.overall_sentiment,
            "sentiment_items": [asdict(item) for item in self.sentiment_items],
            "topics": [asdict(topic) for topic in self.topics],
            "diagnostics": self.diagnostics,
            "media_id": self.media_id,
            "transcription_id": self.transcription_id,
            "user_id": self.user_id,
            "summary": self.summary,
        }
        return to_json_serializable(data)
