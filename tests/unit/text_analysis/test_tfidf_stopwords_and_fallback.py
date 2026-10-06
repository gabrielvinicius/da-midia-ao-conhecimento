import builtins

import pytest

from src.text_analysis.infrastructure.adapters.topic_modeling_tfidf_adapter import (
    TFIDFTopicModelingAdapter,
)
from src.text_analysis.domain import TextChunk


@pytest.mark.asyncio
async def test_tfidf_fallback_when_deps_missing(monkeypatch):
    real_import = builtins.__import__

    def fail_import(name, *args, **kwargs):
        if name.startswith("sklearn") or name.startswith("numpy"):
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fail_import)

    adapter = TFIDFTopicModelingAdapter()
    topics, diag = await adapter.model_topics([TextChunk.from_text("abc")], [], "en")
    assert topics == []
    assert "error" in diag


def test_stopwords_language_selection():
    from src.text_analysis.infrastructure.adapters.stopwords import stop_words_for

    for code in ("pt", "pt-BR", "pt_br", "portuguese"):
        assert "que" in stop_words_for(code)
    assert "the" in stop_words_for("en")
    assert stop_words_for("ja") is None
