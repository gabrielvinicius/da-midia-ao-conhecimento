"""Leitura das análises, só para o dono da mídia ou um administrador."""
from typing import Any

from src.shared.domain.errors import NotFoundError

from ...domain import Analysis
from src.shared.application.access import Requester, ensure_can_access
from ..dtos import GetAnalysisByMediaIdQuery, GetAnalysisQuery, ListTopicsQuery
from ..mappers import analysis_to_dto
from ..ports import AnalysisRepositoryPort


class TextAnalysisReadService:
    def __init__(self, repository: AnalysisRepositoryPort) -> None:
        self.repository = repository

    async def get_analysis(self, query: GetAnalysisQuery, requester: Requester) -> dict[str, Any]:
        analysis = await self._accessible(await self.repository.get(str(query.analysis_id)), requester)
        return analysis_to_dto(analysis).to_dict()

    async def get_analysis_by_media_id(
        self, query: GetAnalysisByMediaIdQuery, requester: Requester
    ) -> dict[str, Any]:
        analysis = await self.repository.get_by_media_id(str(query.media_id))
        return analysis_to_dto(await self._accessible(analysis, requester)).to_dict()

    async def list_topics(self, query: ListTopicsQuery, requester: Requester) -> list[dict[str, Any]]:
        analysis = await self._accessible(await self.repository.get(str(query.analysis_id)), requester)
        return analysis_to_dto(analysis).to_dict()["topics"]

    @staticmethod
    async def _accessible(analysis: Analysis | None, requester: Requester) -> Analysis:
        if analysis is None:
            raise NotFoundError("Análise não encontrada")
        ensure_can_access(analysis.user_id, requester, "Análise não encontrada")
        return analysis
