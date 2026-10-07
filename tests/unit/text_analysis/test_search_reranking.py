"""Busca semântica com reranqueador."""
from types import SimpleNamespace

import pytest

from src.text_analysis.application.ports import RerankerPort
from src.text_analysis.application.services.knowledge_base_service import (
    RERANK_CANDIDATES,
    KnowledgeBaseService,
)


class _Embedder:
    def embed(self, texts, kind="passage"):
        return [[1.0, 0.0]]


class _Repo:
    def __init__(self, contents):
        self.contents = contents
        self.limits = []

    async def semantic_search(self, vector, limit=5, user_id=None):
        self.limits.append(limit)
        rows = [
            (SimpleNamespace(media_id="m", content=c, metadata_json={"start": i * 60.0}), 0.1 * (i + 1))
            for i, c in enumerate(self.contents)
        ]
        return rows[:limit]


class _Reranker(RerankerPort):
    def __init__(self, fail=False):
        self.fail = fail

    def score(self, query, passages):
        if self.fail:
            raise RuntimeError("modelo indisponível")
        return [0.9 if "manifesto" in p else 0.1 for p in passages]


@pytest.mark.asyncio
async def test_reranker_orders_the_candidates_brought_by_the_vectors():
    repo = _Repo(["fala sobre outra coisa", "mais outra coisa", "o manifesto ágil teve 17 autores"])
    service = KnowledgeBaseService(repo, _Embedder(), reranker=_Reranker())

    results = await service.search("quantos assinaram o manifesto?", limit=2)

    assert repo.limits == [RERANK_CANDIDATES]  # busca mais candidatos para reordenar
    assert results[0]["content"] == "o manifesto ágil teve 17 autores"
    assert results[0]["relevance"] == 90.0 and len(results) == 2


@pytest.mark.asyncio
async def test_without_or_with_a_failing_reranker_the_vector_order_stays():
    contents = ["primeiro pelos vetores", "o manifesto ágil"]
    plain = await KnowledgeBaseService(_Repo(contents), _Embedder()).search("manifesto", limit=2)
    failing = await KnowledgeBaseService(_Repo(contents), _Embedder(), reranker=_Reranker(fail=True)).search(
        "manifesto", limit=2
    )

    assert [r["content"] for r in plain] == contents
    assert [r["content"] for r in failing] == contents
