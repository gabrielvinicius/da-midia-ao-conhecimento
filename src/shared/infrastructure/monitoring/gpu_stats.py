"""Uso da GPU medido pelo nvidia-smi e compartilhado pelo Redis.

O alerta de GPU do painel era calculado na API com
torch.cuda.memory_allocated(): o contêiner da API não tem GPU (o valor era
sempre vazio) e, mesmo com GPU, a função só conta a memória do próprio
processo, e não a do worker nem a do Ollama, que são os que a ocupam.

O nvidia-smi mede a placa inteira. O worker pesado, que tem acesso à GPU,
publica a leitura no Redis a cada poucos segundos, inclusive enquanto
processa uma mídia; a API apenas lê. Sem leitura recente (worker parado ou
máquina sem GPU), o valor é desconhecido, e não zero.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import threading
import time
from dataclasses import asdict, dataclass
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)

REDIS_KEY = "monitoring:gpu"
PUBLISH_INTERVAL_SECONDS = 10
TTL_SECONDS = 60  # leitura mais velha que isso é descartada


@dataclass(frozen=True)
class GpuReading:
    memory_used_mb: float
    memory_total_mb: float
    utilization_percent: float

    @property
    def memory_fraction(self) -> float:
        return self.memory_used_mb / self.memory_total_mb if self.memory_total_mb else 0.0


def parse_nvidia_smi(output: str) -> Optional[GpuReading]:
    """Soma as placas: 'memória usada, total, utilização' por linha."""
    used = total = util = 0.0
    lines = [line for line in output.strip().splitlines() if line.strip()]
    if not lines:
        return None
    try:
        for line in lines:
            u, t, g = (float(x) for x in line.split(","))
            used, total, util = used + u, total + t, max(util, g)
    except ValueError:
        return None
    return GpuReading(used, total, util)


def read_nvidia_smi() -> Optional[GpuReading]:
    if not shutil.which("nvidia-smi"):
        return None
    try:
        completed = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.used,memory.total,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True, text=True, timeout=10, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return parse_nvidia_smi(completed.stdout) if completed.returncode == 0 else None


def _redis():
    import redis

    from src.shared.infrastructure.config.settings import settings

    return redis.Redis.from_url(settings.redis_url, socket_timeout=2)


def publish(reading: GpuReading, client=None) -> None:
    client = client or _redis()
    client.set(REDIS_KEY, json.dumps(asdict(reading)), ex=TTL_SECONDS)


def latest(client=None) -> Optional[GpuReading]:
    """Leitura local se esta máquina tem nvidia-smi; senão, a publicada."""
    local = read_nvidia_smi()
    if local:
        return local
    try:
        raw = (client or _redis()).get(REDIS_KEY)
        return GpuReading(**json.loads(raw)) if raw else None
    except Exception as exc:  # monitoramento nunca derruba a requisição
        logger.debug("gpu_stats.read_failed", error=str(exc))
        return None


def start_publisher(interval: float = PUBLISH_INTERVAL_SECONDS) -> bool:
    """Inicia a publicação periódica em segundo plano (só onde há GPU)."""
    if not read_nvidia_smi():
        return False

    def loop():
        while True:
            reading = read_nvidia_smi()
            if reading:
                try:
                    publish(reading)
                except Exception as exc:
                    logger.warning("gpu_stats.publish_failed", error=str(exc))
            time.sleep(interval)

    threading.Thread(target=loop, name="gpu-stats", daemon=True).start()
    logger.info("gpu_stats.publisher_started", interval=interval)
    return True
