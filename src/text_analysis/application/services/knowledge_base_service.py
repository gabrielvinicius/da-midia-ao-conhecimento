"""Service for Semantic Knowledge Base search."""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional
from uuid import UUID
import structlog

from src.text_analysis.application.ports import EmbeddingServicePort, RerankerPort, VectorSearchPort

logger = structlog.get_logger(__name__)

# Candidatos que a busca por vetores traz para o reranqueador ordenar. Medido
# numa aula de 30 min (8 perguntas formuladas com outras palavras): o trecho
# certo ficava em 1º em 4 de 8 só com os vetores e em 7 de 8 reordenando os
# 20 primeiros.
RERANK_CANDIDATES = 20


class KnowledgeBaseService:
    def __init__(
        self,
        vector_repo: VectorSearchPort,
        embedding_service: EmbeddingServicePort,
        reranker: Optional[RerankerPort] = None,
    ):
        self._repo = vector_repo
        self._embedding_service = embedding_service
        self._reranker = reranker

    async def search(
        self, query: str, limit: int = 5, user_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Busca semântica: vetores trazem os candidatos; o reranqueador, se
        configurado, os ordena lendo pergunta e trecho juntos."""
        # O texto da pergunta não vai ao log (dado pessoal); só o tamanho.
        logger.info("knowledge_base.search_started", query_chars=len(query))

        # O modelo de vetores é síncrono e pesado: roda fora do laço da API.
        embeddings = await asyncio.to_thread(self._embedding_service.embed, [query], kind="query")
        candidates = max(limit, RERANK_CANDIDATES) if self._reranker else limit
        results = await self._repo.semantic_search(embeddings[0], limit=candidates, user_id=user_id)

        formatted = [
            {
                "media_id": str(row.media_id),
                "content": row.content,
                "distance": float(distance),
                "relevance": round((1 - float(distance)) * 100, 1),
                "start": (row.metadata_json or {}).get("start"),
                "end": (row.metadata_json or {}).get("end"),
                "metadata": row.metadata_json,
            }
            for row, distance in results
        ]
        if self._reranker and len(formatted) > 1:
            formatted = await self._reranked(query, formatted)
        return formatted[:limit]

    async def _reranked(self, query: str, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ordena pelo reranqueador; se ele falhar, mantém a ordem dos vetores."""
        try:
            scores = await asyncio.to_thread(self._reranker.score, query, [i["content"] for i in items])
        except Exception as exc:
            logger.warning("knowledge_base.rerank_failed", error=str(exc))
            return items
        for item, score in zip(items, scores):
            # A relevância mostrada passa a ser a do reranqueador (0 a 100).
            item["relevance"] = round(float(score) * 100, 1)
        return sorted(items, key=lambda i: i["relevance"], reverse=True)
