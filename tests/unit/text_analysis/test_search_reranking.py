"""Busca semântica com reranqueador."""
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.text_analysis.application.ports import RerankerPort
from src.text_analysis.application.services.knowledge_base_service import (
    KnowledgeBaseService,
    match_level,
    summary_title,
)
from src.text_analysis.domain import Analysis, Document
from src.text_analysis.infrastructure.repositories.inmemory_analysis_repository import InMemoryAnalysisRepository


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
    service = KnowledgeBaseService(repo, _Embedder(), reranker=_Reranker(), rerank_candidates=12)

    results = await service.search("quantos assinaram o manifesto?", limit=2)

    assert repo.limits == [12]  # busca mais candidatos para reordenar (SEARCH_RERANK_CANDIDATES)
    assert results[0]["content"] == "o manifesto ágil teve 17 autores"
    assert results[0]["relevance"] == 90.0 and len(results) == 2


@pytest.mark.asyncio
async def test_every_passage_stays_with_a_level_even_the_unrecognized_ones():
    """Descartar os de nota baixa deixava sem resultado perguntas com outras
    palavras, cujo trecho certo também recebia nota perto de 0."""

    class Scores(RerankerPort):
        def score(self, query, passages):
            return [{"forte": 0.8, "médio": 0.3, "fraco": 0.08, "nada": 0.001}[p] for p in passages]

    service = KnowledgeBaseService(_Repo(["nada", "fraco", "médio", "forte"]), _Embedder(), reranker=Scores())
    results = await service.search("pergunta", limit=10)

    assert [(r["content"], r["match"]) for r in results] == [
        ("forte", "strong"),
        ("médio", "related"),
        ("fraco", "weak"),
        ("nada", "unrecognized"),
    ]
    assert match_level(50) == "strong" and match_level(14.9) == "weak" and match_level(4.9) == "unrecognized"


@pytest.mark.asyncio
async def test_results_carry_the_title_of_the_media_summary():
    analyses = InMemoryAnalysisRepository()
    analysis = Analysis.new(Document.from_payload("t", []), media_id=uuid4())
    analysis.summary = "# A crise da engenharia de software\n\nTexto.\n\n---\n# Apêndice: trechos"
    await analyses.save(analysis)

    class Repo(_Repo):
        async def semantic_search(self, vector, limit=5, user_id=None):
            return [(SimpleNamespace(media_id=analysis.media_id, content="trecho", metadata_json={}), 0.2)]

    results = await KnowledgeBaseService(Repo([]), _Embedder(), analyses=analyses).search("crise")

    assert results[0]["title"] == "A crise da engenharia de software"
    assert results[0]["match"] is None  # sem reranqueador, sem faixa
    assert summary_title("Sem título\n## Seção") is None


@pytest.mark.asyncio
async def test_without_or_with_a_failing_reranker_the_vector_order_stays():
    contents = ["primeiro pelos vetores", "o manifesto ágil"]
    plain = await KnowledgeBaseService(_Repo(contents), _Embedder()).search("manifesto", limit=2)
    failing = await KnowledgeBaseService(_Repo(contents), _Embedder(), reranker=_Reranker(fail=True)).search(
        "manifesto", limit=2
    )

    assert [r["content"] for r in plain] == contents
    assert [r["content"] for r in failing] == contents
