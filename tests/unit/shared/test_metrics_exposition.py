"""Métricas servidas numa porta interna, somando os processos dos workers."""
import os
import socket
import subprocess
import sys
import urllib.request

from src.shared.infrastructure.observability.metrics import exposition


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def test_without_a_port_nothing_is_opened(monkeypatch):
    monkeypatch.delenv("METRICS_PORT", raising=False)
    monkeypatch.setattr(exposition, "_started_port", None)
    assert exposition.start_metrics_server() is None


def test_metrics_are_served_on_the_internal_port_once(monkeypatch):
    port = _free_port()
    monkeypatch.setenv("METRICS_PORT", str(port))
    monkeypatch.delenv("PROMETHEUS_MULTIPROC_DIR", raising=False)
    monkeypatch.setattr(exposition, "_started_port", None)

    assert exposition.start_metrics_server() == port
    assert exposition.start_metrics_server() == port  # a API reinicia o lifespan nos testes
    body = urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics", timeout=5).read().decode()
    assert "python_info" in body


def test_worker_children_are_summed_by_the_parent(tmp_path):
    """Cada processo filho do Celery grava o seu valor; o registro soma todos."""
    child = (
        "from prometheus_client import Counter\n"
        "Counter('tarefas', 'tarefas feitas', ['fila']).labels(fila='q').inc(2)\n"
    )
    env = {**os.environ, "PROMETHEUS_MULTIPROC_DIR": str(tmp_path)}
    for _ in range(2):
        subprocess.run([sys.executable, "-c", child], env=env, check=True)

    parent = (
        "from prometheus_client import generate_latest\n"
        "from src.shared.infrastructure.observability.metrics.exposition import metrics_registry\n"
        "print(generate_latest(metrics_registry()).decode())\n"
    )
    out = subprocess.run([sys.executable, "-c", parent], env=env, check=True, capture_output=True, text=True)
    assert 'tarefas_total{fila="q"} 4.0' in out.stdout
