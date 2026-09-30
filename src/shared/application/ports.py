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


class ProcessingStatsPort(Protocol):
    """Registro e consulta das durações de processamento.

    Usado pela transcrição e pela análise para gravar quanto tempo cada
    tarefa levou, e pela administração para exibir esses tempos.
    """

    async def log_stat(
        self,
        task_type: str,
        processing_duration: float,
        input_size_bytes: int | None = None,
        input_duration: float | None = None,
        model_name: str | None = None,
        status: str = "success",
    ) -> None: ...

    async def summarize(self, days: int | None = None) -> List[Dict[str, Any]]: ...
