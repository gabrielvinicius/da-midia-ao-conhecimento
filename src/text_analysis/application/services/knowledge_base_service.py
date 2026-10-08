"""Service for Semantic Knowledge Base search."""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional
from uuid import UUID
import structlog

from src.text_analysis.application.ports import EmbeddingServicePort, RerankerPort, VectorSearchPort
from src.text_analysis.application.ports.repository import AnalysisRepositoryPort

logger = structlog.get_logger(__name__)

# Candidatos que a busca por vetores traz para o reranqueador ordenar. Medido
# numa aula de 30 min (8 perguntas formuladas com outras palavras): o trecho
# certo ficava em 1º em 4 de 8 só com os vetores e em 7 de 8 reordenando os
# 20 primeiros.
RERANK_CANDIDATES = 20

# Abaixo disso, o reranqueador não reconhece o trecho como resposta. Os trechos
# não são descartados: na avaliação (21 perguntas em 7 mídias), o trecho
# certo de perguntas com outras palavras ("ordem dos fatores" para a
# comutatividade) também recebia 0 a 1,4, como os de uma pergunta sem relação.
# Descartá-los deixava 4 perguntas sem nenhum resultado; a interface avisa
# quando nenhum trecho passa deste valor.
LOW_RELEVANCE = 5.0


def match_level(relevance: float) -> str:
    """Faixa mostrada ao usuário; o número do reranqueador não é uma porcentagem intuitiva."""
    if relevance >= 50:
        return "strong"
    if relevance >= 15:
        return "related"
    if relevance >= LOW_RELEVANCE:
        return "weak"
    return "unrecognized"


def summary_title(summary: Optional[str]) -> Optional[str]:
    """Primeira linha "# ..." do resumo: o assunto da mídia."""
    for line in (summary or "").splitlines():
        if line.startswith("# ") and line[2:].strip():
            return line[2:].strip()
    return None


class KnowledgeBaseService:
    def __init__(
        self,
        vector_repo: VectorSearchPort,
        embedding_service: EmbeddingServicePort,
        reranker: Optional[RerankerPort] = None,
        analyses: Optional[AnalysisRepositoryPort] = None,
    ):
        self._repo = vector_repo
        self._embedding_service = embedding_service
        self._reranker = reranker
        self._analyses = analyses

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
        for item in formatted:
            item["match"] = None  # só o reranqueador dá uma faixa confiável
        if self._reranker and formatted:
            formatted = await self._reranked(query, formatted)
        results = formatted[:limit]
        await self._attach_titles(results)
        return results

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
            item["match"] = match_level(item["relevance"])
        return sorted(items, key=lambda i: i["relevance"], reverse=True)

    async def _attach_titles(self, results: List[Dict[str, Any]]) -> None:
        """Título do resumo de cada mídia, para o resultado dizer de onde vem."""
        if not self._analyses or not results:
            return
        try:
            summaries = await self._analyses.summaries_by_media({r["media_id"] for r in results})
        except Exception as exc:  # o título é um extra: a busca não falha por ele
            logger.warning("knowledge_base.titles_failed", error=str(exc))
            summaries = {}
        for item in results:
            item["title"] = summary_title(summaries.get(item["media_id"]))
