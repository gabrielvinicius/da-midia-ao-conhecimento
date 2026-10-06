from __future__ import annotations

from uuid import UUID

from src.text_analysis.infrastructure.repositories.sqlalchemy_analysis_repository import (
    SqlAlchemyAnalysisRepository,
)


class TextAnalysisDataEraser:
    """Apaga análises, avaliações e trechos indexados de uma mídia (MediaDataEraserPort)."""

    name = "text_analysis"

    def __init__(self, repo: SqlAlchemyAnalysisRepository):
        self._repo = repo

    async def erase(self, media_id: UUID) -> None:
        await self._repo.delete_by_media_id(media_id)


__all__ = ["TextAnalysisDataEraser"]
