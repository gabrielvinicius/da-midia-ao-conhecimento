from src.text_analysis.infrastructure.adapters.provider_catalog_adapter import (
    TextAnalysisProvidersCatalogAdapter,
)
from src.text_analysis.infrastructure.dependencies import registry


def test_catalog_matches_registry_names():
    adapter = TextAnalysisProvidersCatalogAdapter()
    providers = adapter.list_pipeline_providers()

    def names(stage: str):
        return {p.name for p in providers[stage]}

    assert names("text_generation") == {e.name for e in registry.TEXT_GEN_PROVIDERS}
    assert names("sentiment") == {e.name for e in registry.SENTIMENT_PROVIDERS}
    assert names("topic_modeling") == {e.name for e in registry.TOPIC_PROVIDERS}
