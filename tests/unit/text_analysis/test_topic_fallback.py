import pytest

from src.text_analysis.domain import TextChunk
from src.text_analysis.infrastructure.adapters.topic_modeling_bertopic_adapter import (
    BERTopicAdapter,
)


@pytest.mark.asyncio
async def test_short_text_skips_clustering_and_gets_meaningful_topic(monkeypatch):
    """Com poucos trechos o UMAP do BERTopic falha; o texto vira um único tema,
    sem carregar modelos e com palavras-chave que não são palavras vazias."""
    adapter = BERTopicAdapter(model_name="bertopic")
    monkeypatch.setattr(
        adapter, "_ensure_dependencies", lambda: pytest.fail("não deveria carregar modelos")
    )
    chunks = [
        TextChunk.from_text("Então, hoje a gente vai falar de derivadas."),
        TextChunk.from_text("A derivada mede a variação de uma função."),
        TextChunk.from_text("Para calcular a derivada usamos limites, né."),
    ]

    topics, diag = await adapter.model_topics(chunks, [], "pt")

    assert diag["method"] == "fallback"
    (topic,) = topics
    assert topic.keywords[0] == "derivada"
    assert not {"então", "gente", "para", "né", "falar"} & set(topic.keywords[:1])
    assert topic.title.startswith("Derivada")
