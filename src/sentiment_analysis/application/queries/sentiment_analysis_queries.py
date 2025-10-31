"""Read-model access for sentiment analysis results."""

from typing import Optional, Union

from src.sentiment_analysis.domain.sentiment_analysis import SentimentAnalysis
from src.sentiment_analysis.infrastructure.sentiment_analysis_repository import (
    SentimentAnalysisRepository,
)


class SentimentAnalysisQueries:
    """Expose query operations backed by the repository layer."""

    def __init__(self, repository: SentimentAnalysisRepository) -> None:
        self._repository = repository

    async def get_by_media_id(self, media_id: Union[str, None]) -> Optional[SentimentAnalysis]:
        """Return the sentiment analysis associated with ``media_id``."""

        if media_id is None:
            return None
        return await self._repository.get_by_media_id(media_id)

    async def get_by_transcription_id(
        self, transcription_id: str
    ) -> Optional[SentimentAnalysis]:
        """Return a sentiment analysis by its transcription identifier."""

        return await self._repository.find_by_transcription_id(transcription_id)

