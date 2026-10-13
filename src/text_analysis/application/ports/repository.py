"""Repository port for persisting analyses."""

from __future__ import annotations

from typing import Any, List, Optional, Protocol

from abc import ABC, abstractmethod
from uuid import UUID

from src.text_analysis.domain import Analysis, Topic
from src.text_analysis.domain.review import ReviewCard


class AnalysisRepositoryPort(ABC):
    async def save_generated(self, analysis: Analysis) -> str:
        """Grava saída do pipeline somente se não substituir revisão humana."""
        current = await self.get(str(analysis.id))
        if current is not None:
            current.ensure_can_regenerate()
        return await self.save(analysis)

    async def completed_media_ids(self, media_ids: set[UUID]) -> set[UUID]:
        return {
            analysis.media_id for analysis in await self.list_analyses()
            if analysis.pipeline_completed and analysis.media_id in media_ids
        }

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


class ReviewProgressPort(Protocol):
    """Progresso de cada usuário nas perguntas de revisão."""

    async def progress_of(self, user_id: UUID) -> dict:
        """(id da análise, chave da pergunta) -> ReviewCard."""
        ...

    async def card(self, user_id: UUID, analysis_id: UUID, key: str) -> Optional[ReviewCard]: ...

    async def save(self, user_id: UUID, analysis_id: UUID, key: str, card: ReviewCard) -> None: ...


class FeedbackRepositoryPort(Protocol):
    """Avaliações dos usuários sobre os resultados da análise."""

    async def save_feedback(
        self, analysis_id: str, user_id: UUID, score: int, comment: Optional[str] = None
    ) -> Any: ...

    async def list_feedback(self) -> List[Any]:
        """Todas as avaliações (FeedbackRecord), com a mídia da análise."""
        ...
