"""Hardware Advisor e Circuit Breaker para Orquestração Inteligente."""
from __future__ import annotations

import structlog
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any

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
    """Monitor de hardware e gerenciador de redundância ativa (Self-Healing)."""

    def __init__(self, vram_threshold_high: float = 0.85, failure_threshold: int = 3):
        self.vram_threshold_high = vram_threshold_high
        self.failure_threshold = failure_threshold
        # Circuit Breaker state: {provider_name: {failures: int, last_failure: float}}
        self._provider_health: Dict[str, Dict[str, Any]] = {}

    def report_failure(self, provider: str):
        """Registra uma falha de um provedor para acionar circuit breaker."""
        import time
        health = self._provider_health.get(provider, {"failures": 0, "last_failure": 0})
        health["failures"] += 1
        health["last_failure"] = time.time()
        self._provider_health[provider] = health
        logger.warning("advisor.provider_failure_reported", provider=provider, consecutive_failures=health["failures"])

    def report_success(self, provider: str):
        """Reseta o contador de falhas após um sucesso."""
        if provider in self._provider_health:
            self._provider_health[provider]["failures"] = 0

    def is_provider_healthy(self, provider: str) -> bool:
        import time
        health = self._provider_health.get(provider)
        if not health: return True
        
        # Se exceder o threshold, fica em "quarentena" por 5 minutos
        if health["failures"] >= self.failure_threshold:
            if time.time() - health["last_failure"] < 300:
                return False
            else:
                # Tentativa de auto-recuperação (meio-aberto)
                health["failures"] = self.failure_threshold - 1
                return True
        return True

    def get_current_stats(self) -> HardwareStats:
        import psutil
        import torch
        
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        gpu_vram = None
        if torch.cuda.is_available():
            try:
                device = 0
                total_vram = torch.cuda.get_device_properties(device).total_memory
                allocated_vram = torch.cuda.memory_allocated(device)
                reserved_vram = torch.cuda.memory_reserved(device)
                gpu_vram = (allocated_vram + reserved_vram) / total_vram
            except Exception: pass
        return HardwareStats(cpu_usage=cpu, ram_usage=ram, gpu_vram_usage=gpu_vram, gpu_utilization=None)

    def recommend_strategy(self) -> SystemPressure:
        stats = self.get_current_stats()
        if stats.gpu_vram_usage and stats.gpu_vram_usage > 0.98: return SystemPressure.CRITICAL
        if stats.gpu_vram_usage and stats.gpu_vram_usage > self.vram_threshold_high: return SystemPressure.HIGH
        if stats.cpu_usage > 90: return SystemPressure.HIGH
        return SystemPressure.LOW

    def get_redunancy_plan(self, primary_provider: str) -> List[str]:
        """Retorna uma lista de provedores alternativos em ordem de preferência."""
        # Exemplo de planos de contingência
        plans = {
            "qwen3.5:9b": ["gemma4:e4b", "heuristic"],
            "whisper": ["fastwhisper", "vosk"],
            "bertopic": ["sklearn_lda", "keyword_frequency"]
        }
        
        candidates = plans.get(primary_provider, ["heuristic"])
        # Filtra apenas os que estão saudáveis no momento
        return [c for c in candidates if self.is_provider_healthy(c)]
