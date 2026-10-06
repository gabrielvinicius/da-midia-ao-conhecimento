from src.text_analysis.application.config import AnalysisConfig
from src.text_analysis.infrastructure.adapters.text_generation_ollama_adapter import (
    OllamaTextGenerationAdapter,
)
from src.text_analysis.infrastructure.dependencies import registry
from src.text_analysis.infrastructure.dependencies.providers import get_text_generation_adapter


def test_text_generation_only_runs_on_ollama():
    """Sem caminho paralelo pelo Transformers: todo nome vai ao Ollama."""
    from src.shared.infrastructure.model_cache import model_cache

    model_cache.clear()
    adapter = get_text_generation_adapter(AnalysisConfig(llm_model="mistral:7b"))
    assert isinstance(adapter, OllamaTextGenerationAdapter)
    model_cache.clear()


def test_catalog_lists_the_configured_ollama_models():
    from src.shared.infrastructure.config.settings import settings

    assert [e.name for e in registry.TEXT_GEN_PROVIDERS] == [settings.llm_model, settings.llm_fallback_model]
