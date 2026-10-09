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

    @abstractmethod
    async def update_summary(self, analysis_id: str, new_summary: str) -> bool:
        """Grava o resumo corrigido pelo usuário, guardando o original. False se não existir."""
        ...

    @abstractmethod
    async def list_analyses(self, user_id: Optional[str] = None) -> List[Analysis]:
        """Análises de um usuário (ou de todos), das mais novas para as mais antigas."""
        ...

    @abstractmethod
    async def summaries_by_media(self, media_ids: set[str]) -> dict[str, str]:
        """Só o texto do resumo de cada mídia (sem carregar a análise inteira)."""
        ...


class FeedbackRepositoryPort(Protocol):
    """Avaliações dos usuários sobre os resultados da análise."""

    async def save_feedback(
        self, analysis_id: str, user_id: UUID, score: int, comment: Optional[str] = None
    ) -> Any: ...

    async def list_feedback(self) -> List[Any]:
        """Todas as avaliações (FeedbackRecord), com a mídia da análise."""
        ...
