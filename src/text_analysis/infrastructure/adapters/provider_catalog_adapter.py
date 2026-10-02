from __future__ import annotations

from src.shared.application.ports import PipelineProviderCatalogPort
from src.shared.application.provider_catalog import ProviderOption
from src.text_analysis.infrastructure.dependencies.registry import (
    TEXT_GEN_PROVIDERS,
    SENTIMENT_PROVIDERS,
    TOPIC_PROVIDERS,
)


class TextAnalysisProvidersCatalogAdapter(PipelineProviderCatalogPort):
    """Expõe providers do pipeline de análise de texto (sumarização/sentimento/tópicos)."""

    def list_pipeline_providers(self) -> dict[str, list[ProviderOption]]:
        tfidf_available = self._check_tfidf()

        providers = {
            "text_generation": [
                ProviderOption(
                    name=e.name,
                    label=e.label,
                    description=e.description,
                    capabilities={"available": e.available},
                )
                for e in TEXT_GEN_PROVIDERS
            ],
            # Alias para o frontend legacy que espera "summarization"
            "summarization": [
                ProviderOption(
                    name=e.name,
                    label=e.label,
                    description=e.description,
                    capabilities={"available": e.available},
                )
                for e in TEXT_GEN_PROVIDERS
            ],
            "sentiment": [
                ProviderOption(
                    name=e.name,
                    label=e.label,
                    description=e.description,
                    capabilities={"available": e.available},
                )
                for e in SENTIMENT_PROVIDERS
            ],
            "topic_modeling": [
                ProviderOption(
                    name=e.name,
                    label=e.label,
                    description=e.description,
                    capabilities={"available": (tfidf_available if e.name == "tfidf" else e.available)},
                )
                for e in TOPIC_PROVIDERS
            ],
        }
        return providers

    @staticmethod
    def _check_tfidf() -> bool:
        try:  # pragma: no cover - env dependent
            import sklearn  # noqa: F401
            import numpy  # noqa: F401
            return True
        except Exception:
            return False


__all__ = ["TextAnalysisProvidersCatalogAdapter"]
