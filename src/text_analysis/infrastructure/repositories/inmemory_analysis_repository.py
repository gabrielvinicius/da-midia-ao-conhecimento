"""In-memory repository implementation for quick runs/tests."""

from __future__ import annotations

from typing import Dict, List, Optional

from src.text_analysis.application.ports.repository import AnalysisRepositoryPort
from src.text_analysis.domain.entities import Analysis
from src.text_analysis.domain.value_objects import Topic


class InMemoryAnalysisRepository(AnalysisRepositoryPort):
    def __init__(self) -> None:
        self._store: Dict[str, Analysis] = {}

    def save(self, analysis: Analysis) -> str:
        self._store[analysis.id] = analysis
        return analysis.id

    def get(self, analysis_id: str) -> Optional[Analysis]:
        return self._store.get(analysis_id)

    def list_topics(self, analysis_id: str) -> List[Topic]:
        analysis = self._store.get(analysis_id)
        return analysis.topics if analysis else []

