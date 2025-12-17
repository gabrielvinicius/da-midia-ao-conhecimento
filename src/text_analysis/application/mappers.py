"""Mapping domain entities to DTOs."""

from __future__ import annotations

from typing import List

from ..domain import Analysis, SentimentLabel, TextChunk
from .dtos import AnalysisResultDTO, SentimentItemDTO, TopicDTO


def _chunk_lookup(chunks: List[TextChunk]) -> dict[str, TextChunk]:
    return {chunk.id: chunk for chunk in chunks}


def analysis_to_dto(analysis: Analysis) -> AnalysisResultDTO:
    chunk_map = _chunk_lookup(analysis.chunks)
    sentiments = [
        SentimentItemDTO(
            chunk_id=s.chunk_id,
            label=s.label.value,
            score=round(float(s.score), 4),
            text=chunk_map.get(s.chunk_id, TextChunk(s.chunk_id, "")).text,
            start=chunk_map.get(s.chunk_id).start
            if chunk_map.get(s.chunk_id)
            else None,
            end=chunk_map.get(s.chunk_id).end if chunk_map.get(s.chunk_id) else None,
        )
        for s in analysis.sentiments
    ]

    topics = [
            TopicDTO(
                topic_id=getattr(t, "topic_id", getattr(t, "id", 0)),
                title=t.title,
                keywords=t.keywords,
                summary_md=getattr(t, "summary_md", getattr(t, "summary", "")),
                representative_snippets=getattr(t, "snippets", []),
                size=getattr(t, "size", 0),
                diagnostics=getattr(t, "diagnostics", {}) or {},
            )
            for t in analysis.topics
        ]

    overall = analysis.overall_sentiment or SentimentLabel.NEUTRAL
    return AnalysisResultDTO(
        analysis_id=analysis.id,
        document_id=analysis.document.id,
        overall_sentiment=overall.value,
        sentiment_items=sentiments,
        topics=topics,
        diagnostics=analysis.diagnostics,
        media_id=analysis.media_id,
        transcription_id=analysis.transcription_id,
        user_id=analysis.user_id,
    )
