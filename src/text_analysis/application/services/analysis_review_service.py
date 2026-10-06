"""Revisão humana de uma análise: avaliação e correção do resumo."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

import structlog

from src.shared.domain.errors import NotFoundError

from ..access import Requester, ensure_can_access
from ..ports import AnalysisRepositoryPort, FeedbackRepositoryPort

logger = structlog.get_logger(__name__)


class AnalysisReviewService:
    def __init__(self, repository: AnalysisRepositoryPort, feedback_repo: FeedbackRepositoryPort) -> None:
        self._analyses = repository
        self._feedback = feedback_repo

    async def submit_feedback(
        self, analysis_id: UUID, requester: Requester, score: int, comment: Optional[str] = None
    ) -> None:
        await self._ensure_access(analysis_id, requester)
        await self._feedback.save_feedback(str(analysis_id), requester.user_id, score, comment)
        logger.info("text_analysis.feedback_submitted", analysis_id=str(analysis_id), score=score)

    async def correct_summary(self, analysis_id: UUID, requester: Requester, summary: str) -> None:
        """Grava o resumo corrigido; o original da IA fica guardado."""
        await self._ensure_access(analysis_id, requester)
        if not await self._analyses.update_summary(str(analysis_id), summary):
            raise NotFoundError("Análise não encontrada")
        logger.info("text_analysis.summary_corrected_by_human", analysis_id=str(analysis_id))

    async def _ensure_access(self, analysis_id: UUID, requester: Requester) -> None:
        analysis = await self._analyses.get(str(analysis_id))
        if analysis is None:
            raise NotFoundError("Análise não encontrada")
        ensure_can_access(analysis.user_id, requester)
