import pytest

from src.text_analysis.infrastructure.adapters.topic_modeling_tfidf_adapter import (
    TFIDFTopicModelingAdapter,
)
from src.text_analysis.domain import TextChunk


@pytest.mark.asyncio
async def test_tfidf_normalizes_language_codes(monkeypatch):
    # stub deps
    import numpy as np
    from sklearn.cluster import KMeans
    from sklearn.feature_extraction.text import TfidfVectorizer

    adapter = TFIDFTopicModelingAdapter(n_topics=1, max_features=10)

    topics, diag = await adapter.model_topics(
        [
            TextChunk.from_text("a derivada de uma função mede a taxa de variação"),
            TextChunk.from_text("para calcular a derivada usamos o limite"),
        ],
        [],
        "pt-BR",
    )
    # Antes, "portuguese" era passado ao scikit-learn, que só aceita
    # "english": a chamada falhava e nenhum tema era devolvido.
    assert "error" not in diag
    assert topics and "derivada" in topics[0].keywords
    assert not {"de", "a", "para", "uma"} & set(topics[0].keywords)
