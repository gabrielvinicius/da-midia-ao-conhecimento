"""Tela "Servidor": leitura da máquina, da GPU e dos serviços."""
import pytest

from src.admin.infrastructure.adapters import server_status_adapter as adapter
from src.shared.infrastructure.monitoring.gpu_stats import GpuReading


@pytest.fixture
def services(monkeypatch):
    async def ok():
        return True

    async def down():
        return False

    async def ollama():
        return True, ["qwen3.5:9b"]

    monkeypatch.setattr(adapter, "database_ok", ok)
    monkeypatch.setattr(adapter, "redis_ok", down)
    monkeypatch.setattr(adapter, "_ollama_models", ollama)
    monkeypatch.setattr(adapter, "_ping_workers", lambda: ["celery@heavy", "celery@light"])


@pytest.mark.asyncio
async def test_reports_gpu_services_workers_and_loaded_models(services, monkeypatch):
    monkeypatch.setattr(adapter.gpu_stats, "latest", lambda: GpuReading(4096, 16384, 37))

    status = await adapter.ServerStatusAdapter().snapshot()

    assert status.gpu.memory_used_mb == 4096 and status.gpu.utilization_percent == 37
    assert status.services == {"database": True, "redis": False, "ollama": True}
    assert status.workers == ["celery@heavy", "celery@light"]
    assert status.loaded_models == ["qwen3.5:9b"]
    assert status.ram_total_gb > 0 and status.cpu_count > 0


@pytest.mark.asyncio
async def test_without_a_recent_gpu_reading_the_gpu_is_unknown_not_zero(services, monkeypatch):
    monkeypatch.setattr(adapter.gpu_stats, "latest", lambda: None)
    assert (await adapter.ServerStatusAdapter().snapshot()).gpu is None
