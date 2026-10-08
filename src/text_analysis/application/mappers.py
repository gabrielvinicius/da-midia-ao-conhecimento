"""Mapping domain entities to DTOs."""

from __future__ import annotations

from typing import List

from ..domain import Analysis, SentimentLabel, SummarySource, TextChunk
from ..domain.chapters import Chapter, ReviewQuestion
from ..domain.content_genre import parse_genre
from ..domain.grounding import GroundingReport
from .dtos import AnalysisResultDTO, SentimentItemDTO, TopicDTO


def analysis_diagnostics(analysis: Analysis) -> dict:
    """Campos tipados da análise mais os detalhes técnicos, no formato que a
    API e as análises gravadas sempre usaram (``diagnostics``). Chaves
    iniciadas por "_" são temporárias do pipeline e ficam de fora."""
    data = {k: v for k, v in (analysis.diagnostics or {}).items() if not str(k).startswith("_")}
    data["steps"] = dict(analysis.step_status)
    data["step_seconds"] = dict(analysis.step_seconds)
    if analysis.language:
        data["language"] = analysis.language
    if analysis.visual_context:
        data["visual_context"] = list(analysis.visual_context)
    if analysis.summary_source:
        data["summary_source"] = analysis.summary_source.value
    if analysis.grounding:
        data["grounding"] = analysis.grounding.to_dict()
    if analysis.genre:
        data["genre"] = analysis.genre.value
    if analysis.chapters:
        data["chapters"] = [{"start": c.start, "end": c.end, "title": c.title} for c in analysis.chapters]
    if analysis.review_questions:
        data["review_questions"] = [
            {"question": q.question, "answer": q.answer, "start": q.start} for q in analysis.review_questions
        ]
    return data


def restore_from_diagnostics(analysis: Analysis, diagnostics: dict) -> None:
    """Inverso de ``analysis_diagnostics``: separa os campos tipados dos detalhes."""
    rest = dict(diagnostics or {})
    analysis.step_status = dict(rest.pop("steps", None) or {})
    analysis.step_seconds = dict(rest.pop("step_seconds", None) or {})
    analysis.set_language(rest.pop("language", None))
    analysis.visual_context = list(rest.pop("visual_context", None) or [])
    analysis.summary_source = _summary_source(rest.pop("summary_source", None))
    grounding = rest.pop("grounding", None)
    analysis.grounding = GroundingReport.from_dict(grounding) if isinstance(grounding, dict) else None
    analysis.genre = parse_genre(rest.pop("genre", None))
    analysis.chapters = [
        Chapter(start=float(c["start"]), end=float(c["end"]), title=str(c.get("title", "")))
        for c in rest.pop("chapters", None) or []
    ]
    analysis.review_questions = [
        ReviewQuestion(question=str(q.get("question", "")), answer=str(q.get("answer", "")), start=q.get("start"))
        for q in rest.pop("review_questions", None) or []
    ]
    analysis.diagnostics = rest


def _summary_source(value) -> SummarySource | None:
    try:
        return SummarySource(value) if value else None
    except ValueError:  # valor desconhecido de uma versão antiga
        return None


def _chunk_lookup(chunks: List[TextChunk]) -> dict[str, TextChunk]:
    return {chunk.id: chunk for chunk in chunks}


def _map_topic(t, chunks: List[TextChunk]) -> TopicDTO:
    starts = [
        chunks[i].start for i in (t.chunk_indices or []) if 0 <= i < len(chunks) and chunks[i].start is not None
    ]
    return TopicDTO(
        topic_id=t.id,
        title=t.title,
        keywords=t.keywords,
        representative_snippets=list(t.snippets or []),
        size=t.size,
        start=min(starts) if starts else None,
        original_title=getattr(t, "original_title", None),
    )


def analysis_to_dto(analysis: Analysis) -> AnalysisResultDTO:
    chunk_map = _chunk_lookup(analysis.chunks)
    sentiments = [
        SentimentItemDTO(
            chunk_id=s.chunk_id,
            label=s.label.value,
            score=round(float(s.score), 4),
            # Análises antigas não têm os trechos gravados; usa o texto do item.
            text=chunk_map.get(s.chunk_id, TextChunk(s.chunk_id, getattr(s, "text", "") or "")).text,
            start=chunk_map.get(s.chunk_id).start
            if chunk_map.get(s.chunk_id)
            else None,
            end=chunk_map.get(s.chunk_id).end if chunk_map.get(s.chunk_id) else None,
        )
        for s in analysis.sentiments
    ]

    topics = [_map_topic(t, analysis.chunks or []) for t in analysis.topics]

    overall = analysis.overall_sentiment or SentimentLabel.NEUTRAL
    return AnalysisResultDTO(
        analysis_id=str(analysis.id),
        document_id=str(analysis.document.id),
        overall_sentiment=overall.value,
        sentiment_items=sentiments,
        topics=topics,
        diagnostics=analysis_diagnostics(analysis),
        media_id=str(analysis.media_id) if analysis.media_id else None,
        transcription_id=str(analysis.transcription_id) if analysis.transcription_id else None,
        user_id=str(analysis.user_id) if analysis.user_id else None,
        summary=analysis.summary,
    )
