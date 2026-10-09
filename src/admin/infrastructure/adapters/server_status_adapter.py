"""Situação da máquina e dos serviços para a tela "Servidor" do administrador.

CPU e memória são lidas aqui (a API roda na mesma máquina que os workers); a
GPU vem da leitura que o worker pesado publica no Redis (gpu_stats), porque o
contêiner da API não tem acesso à placa.
"""
from __future__ import annotations

import asyncio
from typing import Dict, List, Tuple

import httpx
import psutil
import structlog

from src.admin.application.ports import GpuStatus, ServerStatus
from src.shared.infrastructure.config.settings import settings
from src.shared.infrastructure.monitoring import gpu_stats
from src.shared.infrastructure.monitoring.hardware_advisor import HardwareAdvisor
from src.shared.infrastructure.observability.health.health_check import database_ok, redis_ok

logger = structlog.get_logger(__name__)

TIMEOUT_SECONDS = 2.0


async def _ollama_models() -> Tuple[bool, List[str]]:
    """Se o Ollama responde e quais modelos estão carregados na memória agora."""
    url = settings.ollama_host.rstrip("/") + "/api/ps"
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.get(url)
            response.raise_for_status()
            return True, [m.get("name", "?") for m in response.json().get("models", [])]
    except Exception as exc:
        logger.info("admin.server_status.ollama_unavailable", error=str(exc))
        return False, []


def _ping_workers() -> List[str]:
    """Workers do Celery que responderam ao ping."""
    from src.celery_app import celery

    try:
        replies = celery.control.ping(timeout=TIMEOUT_SECONDS) or []
    except Exception as exc:
        logger.info("admin.server_status.ping_failed", error=str(exc))
        return []
    return sorted(name for reply in replies for name in reply)


class ServerStatusAdapter:
    async def snapshot(self) -> ServerStatus:
        memory = psutil.virtual_memory()
        reading = await asyncio.to_thread(gpu_stats.latest)
        database, redis, (ollama, models), workers = await asyncio.gather(
            database_ok(), redis_ok(), _ollama_models(), asyncio.to_thread(_ping_workers)
        )
        services: Dict[str, bool] = {"database": database, "redis": redis, "ollama": ollama}
        gpu = (
            GpuStatus(reading.memory_used_mb, reading.memory_total_mb, reading.utilization_percent)
            if reading
            else None
        )
        return ServerStatus(
            cpu_percent=psutil.cpu_percent(interval=None),
            cpu_count=psutil.cpu_count() or 0,
            ram_used_gb=round((memory.total - memory.available) / 1024**3, 1),
            ram_total_gb=round(memory.total / 1024**3, 1),
            gpu=gpu,
            pressure=HardwareAdvisor().recommend_strategy().value,
            services=services,
            workers=workers,
            loaded_models=models,
        )


__all__ = ["ServerStatusAdapter"]
