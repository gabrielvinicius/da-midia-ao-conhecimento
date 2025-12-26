from __future__ import annotations

from typing import Dict, List

from src.shared.application.ports import PipelineProviderCatalogPort
from src.shared.application.provider_catalog import ProviderOption
from src.storage.infrastructure.dependencies.providers import StorageServiceFactory


class StorageProvidersCatalogAdapter(PipelineProviderCatalogPort):
    """Expõe apenas providers de storage (upload/download) para o pipeline."""

    def __init__(self, factory: StorageServiceFactory) -> None:
        self._factory = factory

    def list_pipeline_providers(self) -> Dict[str, List[ProviderOption]]:
        providers = []
        for name in self._factory.list_allowed_providers():
            meta = self._factory.provider_meta(name)
            label = meta.get("label", name)
            providers.append(
                ProviderOption(
                    name=name,
                    label=label,
                    description=meta.get("description"),
                    capabilities=meta.get("capabilities", {"upload": True, "download": True}),
                )
            )
        return {"storage": providers}


__all__ = ["StorageProvidersCatalogAdapter"]
