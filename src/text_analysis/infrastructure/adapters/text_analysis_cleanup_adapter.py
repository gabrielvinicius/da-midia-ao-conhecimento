from __future__ import annotations

from uuid import UUID

from src.media_management.application.ports import TextAnalysisCleanupPort
from src.text_analysis.infrastructure.repositories.sqlalchemy_analysis_repository import (
    SqlAlchemyAnalysisRepository,
)


class TextAnalysisCleanupAdapter(TextAnalysisCleanupPort):
    def __init__(self, repo: SqlAlchemyAnalysisRepository):
        self._repo = repo

    async def delete_by_media_id(self, media_id: UUID) -> None:
        await self._repo.delete_by_media_id(media_id)


__all__ = ["TextAnalysisCleanupAdapter"]
