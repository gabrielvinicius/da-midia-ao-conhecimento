"""Devolve ao driver a memória de GPU que o PyTorch guardou em cache."""
from __future__ import annotations

import gc

import structlog

from src.text_analysis.application.ports import ReleasablePort

logger = structlog.get_logger(__name__)


class TorchCacheReleaser(ReleasablePort):
    """O PyTorch mantém a memória já liberada para reutilizá-la; outros
    processos (o Ollama) não a enxergam até ela ser devolvida."""

    async def release(self) -> None:
        try:
            import torch

            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception as exc:  # sem torch ou sem GPU: nada a liberar
            logger.debug("torch_cache_releaser.skipped", error=str(exc))
