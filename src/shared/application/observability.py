"""Portas de observabilidade usadas pela camada de aplicação dos módulos.

Ficam na aplicação do núcleo compartilhado (e não na infraestrutura) porque
são contratos: os adaptadores de log e métricas é que são infraestrutura.
"""
from __future__ import annotations

from typing import Any, Protocol


class MetricsPort(Protocol):
    """Contrato único: assíncrono. Quem chama sempre usa ``await``."""

    async def record_operation(self, **kwargs) -> Any: ...


class LoggerPort(Protocol):
    async def log_operation(self, **kwargs) -> Any: ...
    def info(self, message: str, **kwargs) -> Any: ...
    def warning(self, message: str, **kwargs) -> Any: ...
    def error(self, message: str, **kwargs) -> Any: ...


__all__ = ["MetricsPort", "LoggerPort"]
