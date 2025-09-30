# src/sentiment_analysis/infrastructure/analysis_repository.py
from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.sentiment_analysis.domain.analysis import Analysis, AnalysisType

class AnalysisRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save(self, analysis: Analysis) -> Analysis:
        """Saves an analysis entity to the database."""
        self.db.add(analysis)
        await self.db.commit()
        await self.db.refresh(analysis)
        return analysis

    async def find_by_media_id_and_type(self, media_id: UUID, analysis_type: AnalysisType) -> Optional[Analysis]:
        """Finds an analysis by its associated media ID and type."""
        result = await self.db.execute(
            select(Analysis).where(
                Analysis.media_id == media_id,
                Analysis.type == analysis_type
            )
        )
        return result.scalar_one_or_none()
