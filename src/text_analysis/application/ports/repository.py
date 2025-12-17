"""Repository port for persisting analyses."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from ...domain import Analysis, Topic


class AnalysisRepositoryPort(ABC):
    @abstractmethod
    def save(self, analysis: Analysis) -> str:
        ...

    @abstractmethod
    def get(self, analysis_id: str) -> Optional[Analysis]:
        ...

    @abstractmethod
    def get_by_media_id(self, media_id: str) -> Optional[Analysis]:
        ...

    @abstractmethod
    def list_topics(self, analysis_id: str) -> List[Topic]:
        ...
