"""Leitura do uso de hardware para o painel e o aviso de carga."""
from __future__ import annotations

import structlog
from dataclasses import dataclass
from enum import Enum

logger = structlog.get_logger(__name__)

class SystemPressure(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class HardwareStats:
    cpu_usage: float
    ram_usage: float
    gpu_vram_usage: float | None
    gpu_utilization: float | None

class HardwareAdvisor:
    """Uso de CPU, RAM e GPU (placa inteira, via gpu_stats) e o nível de pressão."""

    def __init__(self, vram_threshold_high: float = 0.85):
        self.vram_threshold_high = vram_threshold_high

    def get_current_stats(self) -> HardwareStats:
        import psutil

        from src.shared.infrastructure.monitoring import gpu_stats

        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        # A placa inteira (worker e Ollama), pelo nvidia-smi; ver gpu_stats.
        gpu = gpu_stats.latest()
        return HardwareStats(
            cpu_usage=cpu,
            ram_usage=ram,
            gpu_vram_usage=gpu.memory_fraction if gpu else None,
            gpu_utilization=gpu.utilization_percent if gpu else None,
        )

    def recommend_strategy(self) -> SystemPressure:
        stats = self.get_current_stats()
        if stats.gpu_vram_usage and stats.gpu_vram_usage > 0.98: return SystemPressure.CRITICAL
        if stats.gpu_vram_usage and stats.gpu_vram_usage > self.vram_threshold_high: return SystemPressure.HIGH
        if stats.cpu_usage > 90: return SystemPressure.HIGH
        return SystemPressure.LOW
