from __future__ import annotations

from typing import Iterable, List

from src.shared.application.ports import PipelineProviderCatalogPort
from src.shared.application.provider_catalog import (
    ProvidersResponse,
    merge_provider_stages,
)


class ProvidersReadService:
    """Read service que agrega providers do pipeline em um único contrato."""

    def __init__(self, catalogs: Iterable[PipelineProviderCatalogPort]) -> None:
        self._catalogs: List[PipelineProviderCatalogPort] = list(catalogs)

    def list_providers(self) -> ProvidersResponse:
        stages = merge_provider_stages(
            *(catalog.list_pipeline_providers() for catalog in self._catalogs)
        )
        return ProvidersResponse(stages=stages)


__all__ = ["ProvidersReadService"]

