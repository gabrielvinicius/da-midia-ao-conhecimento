from __future__ import annotations

from typing import Any, Optional, Protocol, Sequence, Tuple
from uuid import UUID


class IndexedChunk(Protocol):
    """Trecho indexado devolvido pela busca (qualquer objeto com estes campos)."""

    media_id: Any
    content: str
    metadata_json: Optional[dict]


class VectorSearchPort(Protocol):
    """Busca por similaridade nos trechos indexados (pgvector em produção)."""

    async def semantic_search(
        self,
        query_embedding: Sequence[float],
        limit: int = 5,
        user_id: Optional[UUID] = None,
    ) -> Sequence[Tuple[IndexedChunk, float]]:
        """Devolve pares (trecho, distância de cosseno), do mais próximo ao mais distante."""
        ...


class VectorIndexPort(Protocol):
    """Gravação dos trechos e vetores de uma mídia para a busca semântica."""

    async def save_chunks(
        self,
        media_id: UUID,
        chunks: list[dict],
        replace: bool = True,
        user_id: Optional[UUID] = None,
    ) -> Any:
        """Grava os trechos (texto, vetor e metadados); com ``replace``, apaga os anteriores da mídia."""
        ...
