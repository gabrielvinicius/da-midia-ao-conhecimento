"""Uso da GPU: placa inteira pelo nvidia-smi, publicado pelo worker no Redis."""
from unittest.mock import patch

from src.shared.infrastructure.monitoring import gpu_stats
from src.shared.infrastructure.monitoring.gpu_stats import GpuReading, parse_nvidia_smi


def test_parses_nvidia_smi_and_sums_boards():
    reading = parse_nvidia_smi("10240, 12288, 95\n1024, 12288, 10\n")
    assert reading == GpuReading(11264, 24576, 95)
    assert round(reading.memory_fraction, 3) == 0.458
    assert parse_nvidia_smi("") is None
    assert parse_nvidia_smi("[N/A], 12288, 3") is None


class FakeRedis:
    def __init__(self):
        self.data = {}

    def set(self, key, value, ex=None):
        self.data[key] = value

    def get(self, key):
        return self.data.get(key)


def test_api_without_gpu_reads_what_the_worker_published():
    redis = FakeRedis()
    gpu_stats.publish(GpuReading(9000, 12288, 80), client=redis)

    with patch.object(gpu_stats, "read_nvidia_smi", return_value=None):  # contêiner da API
        assert gpu_stats.latest(client=redis) == GpuReading(9000, 12288, 80)
        assert gpu_stats.latest(client=FakeRedis()) is None  # nada publicado: desconhecido
