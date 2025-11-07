from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from src.text_analysis.sentiment_analysis.domain.sentiment_analysis import SentimentAnalysis
from src.text_analysis.summarization.domain.model.summary_aggregate import SummaryAggregate
from src.text_analysis.topic_modeling.domain.topic_modeling import TopicModelingResult
from src.text_analysis.summarization.infrastructure.summarization_repository import (
    SummarizationRepository,
)
from src.text_analysis.sentiment_analysis.infrastructure.sentiment_analysis_repository import (
    SentimentAnalysisRepository,
)
from src.text_analysis.topic_modeling.infrastructure.topic_modeling_repository import (
    TopicModelingRepository,
)

class InMemorySummarizationRepo(SummarizationRepository):
    def __init__(self) -> None:  # type: ignore[super-init-not-called]
        self._by_media: Dict[UUID, SummaryAggregate] = {}
        self._by_id: Dict[UUID, SummaryAggregate] = {}

    async def get_by_media_id(self, media_id: UUID) -> Optional[SummaryAggregate]:
        return self._by_media.get(media_id)

    async def get_by_id(self, summary_id: UUID) -> Optional[SummaryAggregate]:
        return self._by_id.get(summary_id)

    async def add(self, summary: SummaryAggregate) -> SummaryAggregate:
        self._by_media[summary.media_id] = summary
        self._by_id[summary.id] = summary
        return summary

    async def update(self, summary: SummaryAggregate) -> SummaryAggregate:
        self._by_media[summary.media_id] = summary
        self._by_id[summary.id] = summary
        return summary


class InMemorySentimentRepo(SentimentAnalysisRepository):
    def __init__(self) -> None:  # type: ignore[super-init-not-called]
        self._store: Dict[str, SentimentAnalysis] = {}

    async def find_by_transcription_id(self, transcription_id: str) -> Optional[SentimentAnalysis]:
        return self._store.get(transcription_id)

    async def save(self, analysis: SentimentAnalysis) -> SentimentAnalysis:
        self._store[analysis.transcription_id] = analysis
        return analysis

    async def get_by_media_id(self, media_id: str) -> Optional[SentimentAnalysis]:
        for analysis in self._store.values():
            if analysis.media_id == media_id:
                return analysis
        return None


class InMemoryTopicRepo(TopicModelingRepository):
    def __init__(self) -> None:  # type: ignore[super-init-not-called]
        self._store: Dict[UUID, TopicModelingResult] = {}

    async def get_by_media_id(self, media_id: UUID) -> Optional[TopicModelingResult]:
        return self._store.get(media_id)

    async def add(self, result: TopicModelingResult) -> None:
        self._store[result.media_id] = result

    async def update(self, result: TopicModelingResult) -> None:
        self._store[result.media_id] = result
