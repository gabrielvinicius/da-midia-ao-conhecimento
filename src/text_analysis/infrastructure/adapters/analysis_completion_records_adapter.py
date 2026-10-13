"""Consulta as conclusões do módulo de análise para recuperar o estado da mídia."""

from uuid import UUID

from src.text_analysis.application.ports.repository import AnalysisRepositoryPort


class AnalysisCompletionRecordsAdapter:
    def __init__(self, repository: AnalysisRepositoryPort) -> None:
        self._repository = repository

    async def completed_media_ids(self, media_ids: set[UUID]) -> set[UUID]:
        return await self._repository.completed_media_ids(media_ids)
