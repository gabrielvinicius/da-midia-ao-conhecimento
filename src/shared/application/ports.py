from __future__ import annotations

from typing import Any, Dict, List, Protocol

from src.shared.application.provider_catalog import ProviderOption


class PipelineProviderCatalogPort(Protocol):
    """Catálogo de providers expostos para seleção no pipeline.

    Cada bounded context implementa este port para expor apenas os providers
    relevantes ao pipeline (ex.: storage/transcription/ocr/...).
    """

    def list_pipeline_providers(self) -> Dict[str, List[ProviderOption]]: ...


__all__ = ["PipelineProviderCatalogPort"]


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

    async def realtime_factor(self, task_type: str, limit: int = 50) -> float | None: ...
