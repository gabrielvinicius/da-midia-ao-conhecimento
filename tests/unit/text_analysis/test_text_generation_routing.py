from src.text_analysis.application.config import AnalysisConfig
from src.text_analysis.infrastructure.adapters.text_generation_ollama_adapter import (
    OllamaTextGenerationAdapter,
)
from src.text_analysis.infrastructure.dependencies import providers


def test_ollama_model_names_route_to_ollama(monkeypatch):
    from src.shared.infrastructure.model_cache import model_cache

    for name in ["qwen3.5:9b", "llama3.1:8b", "ollama:gemma4:e4b"]:
        model_cache.clear()
        adapter = providers.get_text_generation_adapter(AnalysisConfig(llm_model=name))
        assert isinstance(adapter, OllamaTextGenerationAdapter), name
        assert adapter.config.model == name.removeprefix("ollama:")


def test_default_llm_comes_from_settings(monkeypatch):
    from src.shared.infrastructure.config.settings import settings

    monkeypatch.setattr(settings, "llm_model", "gemma4:e4b")
    assert providers.build_analysis_config().llm_model == "gemma4:e4b"


def test_one_adapter_per_model_in_the_process():
    """Uma instância por modelo no processo, pela chave do cache."""
    from src.shared.infrastructure.model_cache import model_cache

    model_cache.clear()
    first = providers.get_text_generation_adapter(AnalysisConfig(llm_model="qwen3.5:9b"))
    assert providers.get_text_generation_adapter(AnalysisConfig(llm_model="qwen3.5:9b")) is first
    assert providers.get_text_generation_adapter(AnalysisConfig(llm_model="gemma4:e4b")) is not first
    model_cache.clear()
