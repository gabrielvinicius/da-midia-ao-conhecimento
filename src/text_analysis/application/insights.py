"""Leituras sobre várias análises: as perguntas de revisão do aluno e a
qualidade da IA medida pelas correções e avaliações dos usuários.

Funções puras sobre as análises gravadas; os serviços só buscam os dados.
"""
from __future__ import annotations

import datetime
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple
from uuid import UUID

from ..domain import Analysis
from ..domain.review import ReviewCard, normalized, question_key
from src.shared.domain.time.clock import utcnow

# Progresso de cada pergunta de quem estuda: (id da análise, chave da pergunta) -> cartão.
ProgressMap = Dict[Tuple[str, str], ReviewCard]


@dataclass(frozen=True)
class StudyQuestion:
    question: str
    answer: str
    start: Optional[float]  # momento da gravação onde está a resposta
    progress: Optional[ReviewCard] = None  # None: nunca respondida
    due: bool = True  # para revisar agora


@dataclass(frozen=True)
class StudyDeckEntry:
    media_id: Optional[UUID]
    analysis_id: UUID
    questions: List[StudyQuestion]


@dataclass(frozen=True)
class FeedbackRecord:
    """Uma avaliação com o comentário, ligada à mídia da análise. A tela grava
    1 (útil) ou -1 (não foi útil); positiva conta como útil."""

    media_id: Optional[UUID]
    score: int
    comment: Optional[str]
    created_at: Optional[datetime.datetime]


@dataclass(frozen=True)
class CorrectedAnalysis:
    media_id: Optional[UUID]
    parts: List[str]  # "resumo", "temas", "capítulos", "perguntas"


@dataclass(frozen=True)
class AnalysisQualityReport:
    analyses: int
    corrected: dict  # parte -> quantas análises tiveram essa parte corrigida
    useful: int  # avaliações "útil"
    not_useful: int  # avaliações "não foi útil"
    useful_share: Optional[float]  # % de "útil" entre as avaliações
    recent_comments: List[FeedbackRecord] = field(default_factory=list)
    recent_corrections: List[CorrectedAnalysis] = field(default_factory=list)


def study_deck(
    analyses: Iterable[Analysis], progress: Optional[ProgressMap] = None, now: Optional[datetime.datetime] = None
) -> List[StudyDeckEntry]:
    """As perguntas de revisão de cada análise que tem alguma, das mais novas
    para as mais antigas (a ordem que o repositório entregar), com o progresso
    de quem estuda."""
    progress = progress or {}
    now = now or utcnow()

    def question(analysis: Analysis, q) -> StudyQuestion:
        card = progress.get((str(analysis.id), question_key(q.question)))
        return StudyQuestion(q.question, q.answer, q.start, card, card is None or card.is_due(now))

    return [
        StudyDeckEntry(media_id=a.media_id, analysis_id=a.id, questions=[question(a, q) for q in a.review_questions])
        for a in analyses
        if a.review_questions
    ]


@dataclass(frozen=True)
class NotebookEntry:
    media_id: Optional[UUID]
    analysis_id: UUID
    summary: str
    genre: Optional[str]
    topics: List[str]
    chapters: int
    questions: int


def notebook(analyses: Iterable[Analysis]) -> List[NotebookEntry]:
    """Os resumos de todas as análises que têm um, com os temas principais."""
    return [
        NotebookEntry(
            media_id=a.media_id,
            analysis_id=a.id,
            summary=a.summary,
            genre=getattr(a.genre, "value", a.genre),
            topics=[t.title for t in a.topics if t.title][:6],
            chapters=len(a.chapters),
            questions=len(a.review_questions),
        )
        for a in analyses
        if (a.summary or "").strip()
    ]


@dataclass(frozen=True)
class TopicOccurrence:
    media_id: Optional[UUID]
    analysis_id: UUID
    title: str
    keywords: List[str]
    snippet: Optional[str]
    start: Optional[float]  # onde o tema aparece primeiro na gravação


@dataclass(frozen=True)
class TopicGroup:
    title: str
    media_count: int
    occurrences: List[TopicOccurrence]


def _first_start(analysis: Analysis, topic) -> Optional[float]:
    starts = [
        analysis.chunks[i].start
        for i in topic.chunk_indices
        if 0 <= i < len(analysis.chunks) and analysis.chunks[i].start is not None
    ]
    return min(starts) if starts else None


def topic_overview(analyses: Iterable[Analysis]) -> List[TopicGroup]:
    """Temas de todas as mídias, juntos pelo título (sem diferenciar
    maiúsculas, acentos e pontuação); os que aparecem em mais mídias primeiro."""
    groups: Dict[str, List[TopicOccurrence]] = {}
    for analysis in analyses:
        for topic in analysis.topics:
            if not (topic.title or "").strip():
                continue
            groups.setdefault(normalized(topic.title), []).append(
                TopicOccurrence(
                    media_id=analysis.media_id,
                    analysis_id=analysis.id,
                    title=topic.title.strip(),
                    keywords=list(topic.keywords or [])[:5],
                    snippet=(topic.snippets or [None])[0],
                    start=_first_start(analysis, topic),
                )
            )
    result = [
        TopicGroup(title=items[0].title, media_count=len({o.media_id or o.analysis_id for o in items}), occurrences=items)
        for items in groups.values()
    ]
    return sorted(result, key=lambda g: (-g.media_count, normalized(g.title)))


def corrected_parts(analysis: Analysis) -> List[str]:
    """O que o usuário corrigiu: a versão da IA fica guardada na primeira correção."""
    diagnostics = analysis.diagnostics or {}
    parts = []
    if "original_ai_summary" in diagnostics:
        parts.append("resumo")
    if any(t.original_title is not None and t.original_title != t.title for t in analysis.topics):
        parts.append("temas")
    if "original_ai_chapters" in diagnostics:
        parts.append("capítulos")
    if "original_ai_review_questions" in diagnostics:
        parts.append("perguntas")
    return parts


def quality_report(
    analyses: Iterable[Analysis], feedback: Iterable[FeedbackRecord], recent: int = 10
) -> AnalysisQualityReport:
    analyses = list(analyses)
    feedback = list(feedback)
    corrected = Counter()
    corrections: List[CorrectedAnalysis] = []
    for analysis in analyses:
        parts = corrected_parts(analysis)
        corrected.update(parts)
        if parts:
            corrections.append(CorrectedAnalysis(analysis.media_id, parts))
    useful = sum(1 for f in feedback if f.score > 0)
    not_useful = sum(1 for f in feedback if f.score < 0)
    newest_first = sorted(
        (f for f in feedback if (f.comment or "").strip()),
        key=lambda f: f.created_at or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc),
        reverse=True,
    )
    return AnalysisQualityReport(
        analyses=len(analyses),
        corrected={part: corrected.get(part, 0) for part in ("resumo", "temas", "capítulos", "perguntas")},
        useful=useful,
        not_useful=not_useful,
        useful_share=round(useful * 100 / (useful + not_useful), 1) if useful + not_useful else None,
        recent_comments=newest_first[:recent],
        recent_corrections=corrections[:recent],
    )


__all__ = [
    "NotebookEntry",
    "ProgressMap",
    "TopicGroup",
    "TopicOccurrence",
    "notebook",
    "topic_overview",
    "AnalysisQualityReport",
    "CorrectedAnalysis",
    "FeedbackRecord",
    "StudyDeckEntry",
    "StudyQuestion",
    "corrected_parts",
    "quality_report",
    "study_deck",
]
