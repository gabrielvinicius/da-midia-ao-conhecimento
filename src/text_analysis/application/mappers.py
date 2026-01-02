"""Mapping domain entities to DTOs."""

from __future__ import annotations

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
        analysis_id=str(analysis.id),
        document_id=str(analysis.document.id),
        overall_sentiment=overall.value,
        sentiment_items=sentiments,
        topics=topics,
        diagnostics=analysis.diagnostics,
        media_id=str(analysis.media_id) if analysis.media_id else None,
        transcription_id=str(analysis.transcription_id) if analysis.transcription_id else None,
        user_id=str(analysis.user_id) if analysis.user_id else None,
        summary=analysis.summary,
    )
