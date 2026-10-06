"""Apaga as avaliações de um usuário que será excluído (UserDataEraserPort).

As análises do usuário saem com as mídias dele; aqui ficam as avaliações.
"""
from __future__ import annotations

from uuid import UUID

from src.text_analysis.infrastructure.repositories.feedback_repository import FeedbackRepository


class UserFeedbackEraser:
    name = "text_analysis"

    def __init__(self, repository: FeedbackRepository) -> None:
        self._repository = repository

    async def erase(self, user_id: UUID) -> None:
        await self._repository.delete_by_user(user_id)


__all__ = ["UserFeedbackEraser"]
