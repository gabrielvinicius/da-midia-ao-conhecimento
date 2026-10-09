"""Progresso nas perguntas de revisão, por usuário."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.infrastructure.database.unit_of_work import commit as uow_commit
from src.text_analysis.application.insights import ProgressMap
from src.text_analysis.domain.review import ReviewCard
from src.text_analysis.infrastructure.persistence.review_models import ReviewProgressModel


def _card(row: ReviewProgressModel) -> ReviewCard:
    return ReviewCard(
        box=row.box,
        correct_count=row.correct_count,
        wrong_count=row.wrong_count,
        last_answered_at=row.last_answered_at,
        due_at=row.due_at,
    )


class ReviewProgressRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def progress_of(self, user_id: UUID) -> ProgressMap:
        rows = (await self.session.execute(select(ReviewProgressModel).where(ReviewProgressModel.user_id == user_id))).scalars()
        return {(str(row.analysis_id), row.question_key): _card(row) for row in rows}

    async def card(self, user_id: UUID, analysis_id: UUID, key: str) -> ReviewCard | None:
        row = await self._row(user_id, analysis_id, key)
        return _card(row) if row else None

    async def save(self, user_id: UUID, analysis_id: UUID, key: str, card: ReviewCard) -> None:
        row = await self._row(user_id, analysis_id, key)
        if row is None:
            row = ReviewProgressModel(user_id=user_id, analysis_id=analysis_id, question_key=key)
            self.session.add(row)
        row.box, row.correct_count, row.wrong_count = card.box, card.correct_count, card.wrong_count
        row.last_answered_at, row.due_at = card.last_answered_at, card.due_at
        await uow_commit(self.session)

    async def delete_by_user(self, user_id: UUID) -> int:
        result = await self.session.execute(delete(ReviewProgressModel).where(ReviewProgressModel.user_id == user_id))
        await uow_commit(self.session)
        return result.rowcount or 0

    async def _row(self, user_id: UUID, analysis_id: UUID, key: str) -> ReviewProgressModel | None:
        stmt = select(ReviewProgressModel).where(
            ReviewProgressModel.user_id == user_id,
            ReviewProgressModel.analysis_id == analysis_id,
            ReviewProgressModel.question_key == key,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()


__all__ = ["ReviewProgressRepository"]
