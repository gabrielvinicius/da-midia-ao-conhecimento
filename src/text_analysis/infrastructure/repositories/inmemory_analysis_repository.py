"""Repositório em memória, para testes e execuções rápidas."""

from __future__ import annotations

from typing import Optional

from src.text_analysis.application.ports.repository import AnalysisRepositoryPort
from src.text_analysis.domain import Analysis, Topic


class InMemoryAnalysisRepository(AnalysisRepositoryPort):
    def __init__(self) -> None:
        self._store: dict[str, Analysis] = {}

    async def save(self, analysis: Analysis) -> str:
        self._store[str(analysis.id)] = analysis
        return str(analysis.id)

    async def get(self, analysis_id: str) -> Optional[Analysis]:
        return self._store.get(str(analysis_id))

    async def list_topics(self, analysis_id: str) -> list[Topic]:
        analysis = self._store.get(str(analysis_id))
        return analysis.topics if analysis else []

    async def get_by_media_id(self, media_id) -> Optional[Analysis]:
        for analysis in self._store.values():
            if str(analysis.media_id) == str(media_id):
                return analysis
        return None

    async def list_analyses(self, user_id: Optional[str] = None) -> list[Analysis]:
        found = [a for a in self._store.values() if user_id is None or str(a.user_id) == str(user_id)]
        return list(reversed(found))

    async def summaries_by_media(self, media_ids: set[str]) -> dict[str, str]:
        return {
            str(a.media_id): a.summary or "" for a in self._store.values() if str(a.media_id) in media_ids
        }

    async def update_summary(self, analysis_id: str, new_summary: str) -> bool:
        analysis = self._store.get(str(analysis_id))
        if analysis is None:
            return False
        analysis.diagnostics.setdefault("original_ai_summary", analysis.summary)
        analysis.summary = new_summary
        return True
