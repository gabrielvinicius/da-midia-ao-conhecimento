from typing import Any, Optional

from src.shared.domain.errors import NotFoundError
from ...domain import Topic
from ..dtos import (
    GetAnalysisByMediaIdQuery,
    GetAnalysisQuery,
    ListTopicsQuery,
)
from ..mappers import analysis_to_dto
from ..ports import AnalysisRepositoryPort


class TextAnalysisReadService:
    """Read-side service for Text Analysis."""

    def __init__(self, repository: AnalysisRepositoryPort) -> None:
        self.repository = repository

    async def get_analysis(self, query: GetAnalysisQuery) -> dict[str, Any]:
        """Retrieve analysis by ID."""
        analysis = await self.repository.get(str(query.analysis_id))
        if not analysis:
            raise NotFoundError(f"Analysis {query.analysis_id} not found")
        return analysis_to_dto(analysis).to_dict()

    async def get_analysis_by_media_id(
        self, query: GetAnalysisByMediaIdQuery
    ) -> Optional[dict[str, Any]]:
        """Retrieve analysis by Media ID."""
        analysis = await self.repository.get_by_media_id(str(query.media_id))
        return analysis_to_dto(analysis).to_dict() if analysis else None

    async def list_topics(self, query: ListTopicsQuery) -> list[Topic]:
        """List topics for a given analysis."""
        topics = await self.repository.list_topics(str(query.analysis_id))
        if topics is None:
            raise NotFoundError(f"Analysis {query.analysis_id} not found")
        return topics
