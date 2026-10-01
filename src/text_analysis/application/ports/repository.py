"""Repository port for persisting analyses."""

from __future__ import annotations

from typing import Any, List, Optional, Protocol

from abc import ABC, abstractmethod
from uuid import UUID

from src.text_analysis.domain import Analysis, Topic


class AnalysisRepositoryPort(ABC):
    @abstractmethod
    async def save(self, analysis: Analysis) -> str:
        ...

    @abstractmethod
    async def get(self, analysis_id: str) -> Optional[Analysis]:
        ...

    @abstractmethod
    async def get_by_media_id(self, media_id: str) -> Optional[Analysis]:
        ...

    @abstractmethod
    async def list_topics(self, analysis_id: str) -> List[Topic]:
        ...


class FeedbackRepositoryPort(Protocol):
    """Avaliações dos usuários sobre os resultados da análise."""

    async def save_feedback(
        self, analysis_id: str, user_id: UUID, score: int, comment: Optional[str] = None
    ) -> Any: ...
