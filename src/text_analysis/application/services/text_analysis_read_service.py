from typing import Any, Optional

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

    async def get_analysis(self, query: GetAnalysisQuery) -> dict[str, Any]:
        """Retrieve analysis by ID."""
        analysis = await self.repository.get(str(query.analysis_id))
        if not analysis:
            raise DomainError(f"Analysis {query.analysis_id} not found")
        return analysis_to_dto(analysis).to_dict()

    async def get_analysis_by_media_id(
        self, query: GetAnalysisByMediaIdQuery
    ) -> Optional[dict[str, Any]]:
        """Retrieve analysis by Media ID."""
        import structlog
        logger = structlog.get_logger(__name__)
        logger.info("debug.read_service.start", media_id=str(query.media_id))
        
        try:
            analysis = await self.repository.get_by_media_id(str(query.media_id))
            if not analysis:
                logger.info("debug.read_service.repo_returned_none", media_id=str(query.media_id))
                return None
            
            logger.info("debug.read_service.found", id=str(analysis.id))
            return analysis_to_dto(analysis).to_dict()
        except Exception as e:
            logger.error("debug.read_service.error", error=str(e))
            raise

    async def list_topics(self, query: ListTopicsQuery) -> list[Topic]:
        """List topics for a given analysis."""
        topics = await self.repository.list_topics(str(query.analysis_id))
        if topics is None:
            raise DomainError(f"Analysis {query.analysis_id} not found")
        return topics
