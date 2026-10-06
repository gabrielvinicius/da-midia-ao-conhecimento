"""Exposição das métricas do Prometheus fora da API pública.

API e workers servem as métricas numa porta interna (``METRICS_PORT``),
alcançável só pela rede do Compose. Nos workers do Celery, cada tarefa roda
num processo filho; com ``PROMETHEUS_MULTIPROC_DIR`` definido, os processos
gravam as métricas em arquivos e o processo principal soma todos ao servir.
"""
from __future__ import annotations

import os

from prometheus_client import REGISTRY, CollectorRegistry, multiprocess, start_http_server

METRICS_PORT_ENV = "METRICS_PORT"
MULTIPROC_DIR_ENV = "PROMETHEUS_MULTIPROC_DIR"

_started_port: int | None = None


def metrics_registry() -> CollectorRegistry:
    """Registro a servir: o agregado dos processos ou o do próprio processo."""
    if os.getenv(MULTIPROC_DIR_ENV):
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
        return registry
    return REGISTRY


def start_metrics_server() -> int | None:
    """Abre a porta interna de métricas, se configurada. Devolve a porta."""
    global _started_port
    port = os.getenv(METRICS_PORT_ENV)
    if not port or _started_port is not None:
        return _started_port
    start_http_server(int(port), registry=metrics_registry())
    _started_port = int(port)
    return _started_port


def mark_process_dead(pid: int) -> None:
    """Descarta os medidores (gauges) de um processo filho que terminou."""
    if os.getenv(MULTIPROC_DIR_ENV):
        multiprocess.mark_process_dead(pid)


__all__ = ["metrics_registry", "start_metrics_server", "mark_process_dead"]
