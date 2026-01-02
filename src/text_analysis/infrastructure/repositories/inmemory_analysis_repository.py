"""In-memory repository implementation for quick runs/tests."""

from __future__ import annotations

from typing import Optional

from src.text_analysis.application.ports.repository import AnalysisRepositoryPort
from src.text_analysis.domain import Analysis, Topic


class InMemoryAnalysisRepository(AnalysisRepositoryPort):
    def __init__(self) -> None:
        self._store: dict[str, Analysis] = {}

    async def save(self, analysis: Analysis) -> str:
        self._store[analysis.id] = analysis
        return analysis.id

    async def get(self, analysis_id: str) -> Optional[Analysis]:
        return self._store.get(analysis_id)

    async def list_topics(self, analysis_id: str) -> list[Topic]:
        analysis = self._store.get(analysis_id)
        return analysis.topics if analysis else []

    # Optional helper for compatibility
    async def get_by_media_id(self, media_id) -> Optional[Analysis]:
        for analysis in self._store.values():
            if str(getattr(analysis, "media_id", "")) == str(media_id):
                return analysis
        return None
