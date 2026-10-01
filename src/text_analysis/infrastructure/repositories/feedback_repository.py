"""Repository for managing user feedback."""
from __future__ import annotations

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from src.text_analysis.infrastructure.persistence.feedback_models import FeedbackModel
from src.shared.infrastructure.database.unit_of_work import commit as uow_commit

class FeedbackRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_feedback(
        self, 
        analysis_id: str, 
        user_id: UUID, 
        score: int, 
        comment: str | None = None,
        aspect: str = "overall"
    ) -> FeedbackModel:
        record = FeedbackModel(
            analysis_id=analysis_id,
            user_id=user_id,
            score=score,
            comment=comment,
            aspect=aspect
        )
        self.session.add(record)
        await uow_commit(self.session)
        return record

    async def get_stats_for_analysis(self, analysis_id: str):
        # Future: aggregation logic for average scores
        pass
