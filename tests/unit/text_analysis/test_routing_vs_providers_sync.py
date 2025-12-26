from src.text_analysis.infrastructure.dependencies import registry


def test_routing_is_subset_of_providers_targets():
    provider_names = {p.name for p in registry.TEXT_GEN_PROVIDERS}
    # routing values must exist either as provider name or be the llama3 alias
    for alias, target in registry.TEXT_GEN_ROUTING.items():
        assert target == "llama3" or target in provider_names


def test_providers_have_targets():
    assert all(p.target for p in registry.TEXT_GEN_PROVIDERS)
