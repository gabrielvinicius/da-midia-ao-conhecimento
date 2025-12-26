from __future__ import annotations

from typing import Any, Dict, List, Protocol

from src.shared.application.provider_catalog import ProviderOption


class ModuleRegistryPort(Protocol):
    """Expose domain service registry for diagnostics or cross-cutting access."""

    def attach(self, app: Any) -> None: ...
    def get(self) -> Any: ...


class PipelineProviderCatalogPort(Protocol):
    """Catálogo de providers expostos para seleção no pipeline.

    Cada bounded context implementa este port para expor apenas os providers
    relevantes ao pipeline (ex.: storage/transcription/ocr/...).
    """

    def list_pipeline_providers(self) -> Dict[str, List[ProviderOption]]: ...


__all__ = ["ModuleRegistryPort", "PipelineProviderCatalogPort"]
