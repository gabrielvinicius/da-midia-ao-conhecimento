"""Leitura das análises, só para o dono da mídia ou um administrador."""
from typing import Any

from ...domain.review import DEFAULT_SCHEDULE, ReviewSchedule

from src.shared.domain.errors import NotFoundError

from ...domain import Analysis
from src.shared.application.access import Requester, ensure_can_access
from ..dtos import GetAnalysisByMediaIdQuery, GetAnalysisQuery, ListTopicsQuery
from ..insights import NotebookEntry, StudyDeckEntry, TopicGroup, notebook, study_deck, topic_overview
from ..mappers import analysis_to_dto
from ..ports.repository import AnalysisRepositoryPort, ReviewProgressPort


class TextAnalysisReadService:
    def __init__(
        self,
        repository: AnalysisRepositoryPort,
        progress: ReviewProgressPort | None = None,
        schedule: ReviewSchedule = DEFAULT_SCHEDULE,
    ) -> None:
        self.repository = repository
        self._progress = progress
        self._schedule = schedule

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

    async def study_deck(self, requester: Requester) -> list[StudyDeckEntry]:
        """Perguntas de revisão de todas as análises de quem pede."""
        analyses = await self.repository.list_analyses(str(requester.user_id))
        progress = await self._progress.progress_of(requester.user_id) if self._progress else {}
        return study_deck(analyses, progress, schedule=self._schedule)

    async def notebook(self, requester: Requester) -> list[NotebookEntry]:
        """Os resumos de todas as mídias de quem pede."""
        return notebook(await self.repository.list_analyses(str(requester.user_id)))

    async def topic_overview(self, requester: Requester) -> list[TopicGroup]:
        """Os temas de todas as mídias de quem pede, juntos pelo título."""
        return topic_overview(await self.repository.list_analyses(str(requester.user_id)))

    @staticmethod
    async def _accessible(analysis: Analysis | None, requester: Requester) -> Analysis:
        if analysis is None:
            raise NotFoundError("Análise não encontrada")
        ensure_can_access(analysis.user_id, requester, "Análise não encontrada")
        return analysis
