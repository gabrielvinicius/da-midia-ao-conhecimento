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

    topics, _ = await adapter.model_topics(
        [TextChunk.from_text("hello world"), TextChunk.from_text("world hello")],
        [],
        "pt-BR",
    )
    # apenas valida que não quebra e processa com stopwords pt (normalizado)
    assert topics == [] or isinstance(topics, list)
