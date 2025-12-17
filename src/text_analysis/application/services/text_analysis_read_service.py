from typing import Any, Dict, List, Optional

from ...domain.errors import DomainError
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

    def get_analysis(self, query: GetAnalysisQuery) -> Dict[str, Any]:
        """Retrieve analysis by ID."""
        analysis = self.repository.get(query.analysis_id)
        if not analysis:
            raise DomainError(f"Analysis {query.analysis_id} not found")
        return analysis_to_dto(analysis).to_dict()

    def get_analysis_by_media_id(
        self, query: GetAnalysisByMediaIdQuery
    ) -> Optional[Dict[str, Any]]:
        """Retrieve analysis by Media ID."""
        analysis = self.repository.get_by_media_id(query.media_id)
        if not analysis:
            return None
        return analysis_to_dto(analysis).to_dict()

    def list_topics(self, query: ListTopicsQuery) -> List[Topic]:
        """List topics for a given analysis."""
        topics = self.repository.list_topics(query.analysis_id)
        if topics is None:
            raise DomainError(f"Analysis {query.analysis_id} not found")
        return topics
