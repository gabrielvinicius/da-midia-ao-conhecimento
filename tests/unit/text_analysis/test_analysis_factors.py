"""Fatores da análise ligados e desligados por configuração (ANALYSIS_FACTORS)."""
from uuid import uuid4

import pytest

from src.text_analysis.application.config import OPTIONAL_FACTORS, AnalysisConfig
from src.text_analysis.domain import Analysis, Document
from src.text_analysis.infrastructure.adapters.chunking_simple_adapter import SimpleChunker
from src.text_analysis.infrastructure.dependencies import pipeline_factory, providers


class FakeEmbeddings:
    def embed(self, texts, kind="passage"):
        return [[1.0, 0.0] for _ in texts]


class FakeGenerator:
    last_used_reserve = False
    last_prompt_tokens = None
    last_prompt_truncated = False

    async def summarize_topic(self, title, content, keywords, language, max_tokens=None):
        return "A aula explica como calcular derivadas de funções simples com exemplos."

    async def generate_title(self, *args, **kwargs):
        return "Tema"

    async def release(self):
        return None


class Unused:
    """Modelo de um fator desligado: não pode ser construído."""

    def __init__(self, *args, **kwargs):
        raise AssertionError("o modelo de um fator desligado não deveria ser carregado")


@pytest.fixture
def fake_models(monkeypatch):
    built = []

    def factory(name, value):
        def build(_config):
            built.append(name)
            return value() if callable(value) and isinstance(value, type) else value
        return build

    monkeypatch.setattr(providers, "get_embedding_adapter", factory("embeddings", FakeEmbeddings()))
    monkeypatch.setattr(providers, "get_text_generation_adapter", factory("llm", FakeGenerator()))
    monkeypatch.setattr(providers, "get_sentiment_adapter", factory("sentiment", Unused))
    monkeypatch.setattr(providers, "get_topic_modeling_adapter", factory("topics", Unused))
    monkeypatch.setattr(providers, "get_chunker_adapter", lambda _c: SimpleChunker())
    return built


def _names(components):
    return [step.name for step in components.pipeline.steps]


def test_all_factors_are_on_by_default():
    assert AnalysisConfig().factors == OPTIONAL_FACTORS


@pytest.mark.parametrize(
    "factors, absent",
    [
        (frozenset(), {"sentiment", "topic_modeling", "topic_titles", "grounding_check"}),
        (frozenset({"grounding"}), {"sentiment", "topic_modeling", "topic_titles"}),
    ],
)
def test_switched_off_factors_leave_the_pipeline_and_their_models_are_not_loaded(fake_models, factors, absent):
    components = pipeline_factory.build_analysis_pipeline(AnalysisConfig(factors=factors), session=None)
    names = _names(components)

    assert not absent & set(names)
    # A base da busca e da página da mídia continua.
    for core in ("chunking", "chunk_embedding", "knowledge_indexing", "synthesis"):
        assert core in names
    assert "sentiment" not in fake_models and "topics" not in fake_models


@pytest.mark.asyncio
async def test_analysis_without_topics_and_sentiment_still_summarizes_and_checks(fake_models):
    components = pipeline_factory.build_analysis_pipeline(
        AnalysisConfig(factors=frozenset({"grounding"})), session=None
    )

    class Vectors:
        async def save_chunks(self, media_id, records, user_id=None):
            self.saved = records

    components.pipeline.steps = [
        step if step.name != "knowledge_indexing" else type(step)(Vectors()) for step in components.pipeline.steps
    ]
    text = "A aula explica derivadas. " * 20
    analysis = Analysis(id=uuid4(), document=Document(id=uuid4(), text=text), media_id=uuid4())

    result = await components.pipeline.run(analysis)

    assert set(result.step_status.values()) == {"ok"}
    assert result.summary and result.topics == [] and result.overall_sentiment is None
    assert result.diagnostics["indexed_chunks"] == len(result.chunks)
    assert result.grounding is not None


def test_factors_come_from_the_environment(monkeypatch):
    from src.shared.infrastructure.config.settings import settings

    monkeypatch.setattr(settings, "analysis_factors", " topics , grounding ")
    assert providers.build_analysis_config().factors == {"topics", "grounding"}

    monkeypatch.setattr(settings, "analysis_factors", "")
    assert providers.build_analysis_config().factors == frozenset()

    monkeypatch.setattr(settings, "analysis_factors", "topics,emotion")
    with pytest.raises(ValueError, match="emotion"):
        providers.build_analysis_config()


def test_visual_description_can_be_switched_off(monkeypatch):
    from src.media_processing.infrastructure.dependencies import builders
    from src.shared.infrastructure.config.settings import settings

    monkeypatch.setattr(settings, "visual_provider", "none")
    assert builders._visual_describer() is None
