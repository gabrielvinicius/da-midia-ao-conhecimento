# src/topic_modeling/application/queries/topic_modeling_queries.py
from typing import Optional

from src.topic_modeling.domain.topic_modeling import TopicModelingResult
from src.topic_modeling.infrastructure.topic_modeling_repository import TopicModelingRepository


class TopicModelingQueries:
    """Handles all read-only operations for topic modeling results."""
    def __init__(self, repository: TopicModelingRepository):
        self.repository = repository

    async def get_by_media_id(self, media_id: str) -> Optional[TopicModelingResult]:
        """Retrieves a topic modeling result by its associated media ID."""
        return await self.repository.find_by_media_id(media_id)
