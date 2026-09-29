from src.text_analysis.application.config import AnalysisConfig
from src.text_analysis.infrastructure.adapters.text_generation_ollama_adapter import (
    OllamaTextGenerationAdapter,
)
from src.text_analysis.infrastructure.dependencies import providers


def test_ollama_model_names_route_to_ollama(monkeypatch):
    monkeypatch.setattr(providers, "_CACHED_TEXTGEN_ADAPTER", None)
    for name in ["qwen3.5:9b", "llama3.1:8b", "ollama:gemma4:e4b"]:
        monkeypatch.setattr(providers, "_CACHED_TEXTGEN_ADAPTER", None)
        adapter = providers.get_text_generation_adapter(AnalysisConfig(llm_model=name))
        assert isinstance(adapter, OllamaTextGenerationAdapter), name
        assert adapter.config.model == name.removeprefix("ollama:")


def test_default_llm_comes_from_settings(monkeypatch):
    from src.shared.infrastructure.config.settings import settings

    monkeypatch.setattr(settings, "llm_model", "gemma4:e4b")
    assert AnalysisConfig().llm_model == "gemma4:e4b"
