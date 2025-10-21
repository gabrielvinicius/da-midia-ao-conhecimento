# src/sentiment_analysis/application/queries/analysis_queries.py
from typing import Optional
from uuid import UUID

from src.sentiment_analysis.domain.analysis import Analysis, AnalysisType
# FIXED: Application should not import Infrastructure directly
from src.shared.application.dependency_injection import get_sentiment_analysis_repository

class AnalysisQueries:
    """Handles all read-only operations for analyses."""
    def __init__(self, analysis_repository: AnalysisRepository):
        self.analysis_repository = analysis_repository

    async def get_by_media_id_and_type(self, media_id: UUID, analysis_type: AnalysisType) -> Optional[Analysis]:
        """Retrieves an analysis by its media ID and type."""
        return await self.analysis_repository.find_by_media_id_and_type(media_id, analysis_type)
