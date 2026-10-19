"""Revisão humana de uma análise: avaliação e correção do resumo."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

import structlog

from src.shared.domain.errors import NotFoundError

from src.shared.application.access import Requester, ensure_can_access
from ...domain import Analysis
from ...domain.chapters import Chapter, ReviewQuestion
from ..insights import AnalysisQualityReport, ReviewProgress, quality_report, review_progress
from ..ports import AnalysisRepositoryPort, FeedbackRepositoryPort
from ..ports.repository import ReviewProgressPort
from ...domain.review import DEFAULT_SCHEDULE, ReviewCard, ReviewSchedule, question_key
from src.shared.domain.time.clock import utcnow

logger = structlog.get_logger(__name__)


class AnalysisReviewService:
    def __init__(
        self,
        repository: AnalysisRepositoryPort,
        feedback_repo: FeedbackRepositoryPort,
        progress: ReviewProgressPort | None = None,
        schedule: ReviewSchedule = DEFAULT_SCHEDULE,
    ) -> None:
        self._analyses = repository
        self._feedback = feedback_repo
        self._progress = progress
        self._schedule = schedule

    async def submit_feedback(
        self, analysis_id: UUID, requester: Requester, score: int, comment: Optional[str] = None
    ) -> None:
        await self._ensure_access(analysis_id, requester)
        await self._feedback.save_feedback(str(analysis_id), requester.user_id, score, comment)
        logger.info("text_analysis.feedback_submitted", analysis_id=str(analysis_id), score=score)

    async def answer_question(
        self, analysis_id: UUID, requester: Requester, question: str, correct: bool
    ) -> ReviewProgress:
        """Registra se o aluno acertou a pergunta e devolve quando revê-la."""
        analysis = await self._ensure_access(analysis_id, requester)
        key = question_key(question)
        if self._progress is None or not any(question_key(q.question) == key for q in analysis.review_questions):
            raise NotFoundError("Pergunta não encontrada")
        card = await self._progress.card(requester.user_id, analysis.id, key) or ReviewCard()
        card = card.answered(correct, utcnow(), self._schedule)
        await self._progress.save(requester.user_id, analysis.id, key, card)
        return review_progress(card, self._schedule)

    async def quality_report(self) -> AnalysisQualityReport:
        """Correções e avaliações de todas as análises (para o administrador)."""
        return quality_report(await self._analyses.list_analyses(), await self._feedback.list_feedback())

    async def correct_summary(self, analysis_id: UUID, requester: Requester, summary: str) -> None:
        """Grava o resumo corrigido; o original da IA fica guardado."""
        await self._ensure_access(analysis_id, requester)
        if not await self._analyses.update_summary(str(analysis_id), summary):
            raise NotFoundError("Análise não encontrada")
        logger.info("text_analysis.summary_corrected_by_human", analysis_id=str(analysis_id))

    async def rename_topic(self, analysis_id: UUID, requester: Requester, topic_id: int, title: str) -> None:
        analysis = await self._ensure_access(analysis_id, requester)
        analysis.rename_topic(topic_id, title.strip())
        await self._analyses.save(analysis)
        logger.info("text_analysis.topic_renamed_by_human", analysis_id=str(analysis_id))

    async def correct_study_aids(
        self,
        analysis_id: UUID,
        requester: Requester,
        chapters: list[Chapter],
        questions: list[ReviewQuestion],
    ) -> None:
        """Capítulos e perguntas revisados; a versão da IA fica guardada."""
        analysis = await self._ensure_access(analysis_id, requester)
        analysis.correct_study_aids(chapters, questions)
        await self._analyses.save(analysis)
        logger.info("text_analysis.study_aids_corrected_by_human", analysis_id=str(analysis_id))

    async def _ensure_access(self, analysis_id: UUID, requester: Requester) -> Analysis:
        analysis = await self._analyses.get(str(analysis_id))
        if analysis is None:
            raise NotFoundError("Análise não encontrada")
        ensure_can_access(analysis.user_id, requester, "Análise não encontrada")
        return analysis
