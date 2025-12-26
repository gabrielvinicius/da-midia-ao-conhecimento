import pytest

from src.text_analysis.application.config import AnalysisConfig
from src.text_analysis.infrastructure.dependencies.providers import get_text_generation_adapter


def test_text_generation_accepts_known_alias():
    cfg = AnalysisConfig(llm_model="mistral-7b")
    adapter = get_text_generation_adapter(cfg)
    assert hasattr(adapter, "model_name")


def test_text_generation_rejects_unknown():
    cfg = AnalysisConfig(llm_model="hf:unknown-model-xyz")
    with pytest.raises(ValueError):
        get_text_generation_adapter(cfg)
