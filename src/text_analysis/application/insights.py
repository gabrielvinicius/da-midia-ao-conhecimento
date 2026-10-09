"""Leituras sobre várias análises: as perguntas de revisão do aluno e a
qualidade da IA medida pelas correções e avaliações dos usuários.

Funções puras sobre as análises gravadas; os serviços só buscam os dados.
"""
from __future__ import annotations

import datetime
from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable, List, Optional
from uuid import UUID

from ..domain import Analysis


@dataclass(frozen=True)
class StudyQuestion:
    question: str
    answer: str
    start: Optional[float]  # momento da gravação onde está a resposta


@dataclass(frozen=True)
class StudyDeckEntry:
    media_id: Optional[UUID]
    analysis_id: UUID
    questions: List[StudyQuestion]


@dataclass(frozen=True)
class FeedbackRecord:
    """Uma avaliação (1 a 5) com o comentário, ligada à mídia da análise."""

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
    ratings: dict  # nota (1 a 5) -> quantas
    rating_count: int
    rating_average: Optional[float]
    recent_comments: List[FeedbackRecord] = field(default_factory=list)
    recent_corrections: List[CorrectedAnalysis] = field(default_factory=list)


def study_deck(analyses: Iterable[Analysis]) -> List[StudyDeckEntry]:
    """As perguntas de revisão de cada análise que tem alguma, das mais novas
    para as mais antigas (a ordem que o repositório entregar)."""
    return [
        StudyDeckEntry(
            media_id=a.media_id,
            analysis_id=a.id,
            questions=[StudyQuestion(q.question, q.answer, q.start) for q in a.review_questions],
        )
        for a in analyses
        if a.review_questions
    ]


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
    scores = [f.score for f in feedback if 1 <= f.score <= 5]
    newest_first = sorted(
        (f for f in feedback if (f.comment or "").strip()),
        key=lambda f: f.created_at or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc),
        reverse=True,
    )
    return AnalysisQualityReport(
        analyses=len(analyses),
        corrected={part: corrected.get(part, 0) for part in ("resumo", "temas", "capítulos", "perguntas")},
        ratings={score: scores.count(score) for score in range(1, 6)},
        rating_count=len(scores),
        rating_average=round(sum(scores) / len(scores), 2) if scores else None,
        recent_comments=newest_first[:recent],
        recent_corrections=corrections[:recent],
    )


__all__ = [
    "AnalysisQualityReport",
    "CorrectedAnalysis",
    "FeedbackRecord",
    "StudyDeckEntry",
    "StudyQuestion",
    "corrected_parts",
    "quality_report",
    "study_deck",
]
