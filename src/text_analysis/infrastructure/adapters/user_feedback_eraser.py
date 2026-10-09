"""Apaga as avaliações de um usuário que será excluído (UserDataEraserPort).

As análises do usuário saem com as mídias dele; aqui ficam as avaliações e o
progresso nas perguntas de revisão.
"""
from __future__ import annotations

from uuid import UUID

from typing import Optional

from src.text_analysis.infrastructure.repositories.feedback_repository import FeedbackRepository
from src.text_analysis.infrastructure.repositories.review_progress_repository import ReviewProgressRepository


class UserFeedbackEraser:
    name = "text_analysis"

    def __init__(self, repository: FeedbackRepository, progress: Optional[ReviewProgressRepository] = None) -> None:
        self._repository = repository
        self._progress = progress

    async def erase(self, user_id: UUID) -> None:
        await self._repository.delete_by_user(user_id)
        if self._progress is not None:
            await self._progress.delete_by_user(user_id)


__all__ = ["UserFeedbackEraser"]
