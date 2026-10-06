"""As filas dos workers no docker-compose são as mesmas do código.

Um worker que não escuta a fila para a qual a tarefa é enviada deixa a
tarefa parada para sempre, sem erro em lugar nenhum.
"""
import re
from pathlib import Path

import pytest

from src.shared.events.integration_events import HEAVY_WORKER_QUEUES, LIGHT_WORKER_QUEUES

ROOT = Path(__file__).resolve().parents[2]


def _worker_queues(compose: str) -> list[set[str]]:
    text = (ROOT / compose).read_text(encoding="utf-8")
    return [set(q.split(",")) for q in re.findall(r"celery .*? worker .*?-Q (\S+)", text)]


@pytest.mark.parametrize("compose", ["docker-compose.yml", "docker-compose.cpu.yml"])
def test_heavy_worker_listens_to_every_heavy_queue(compose):
    assert set(HEAVY_WORKER_QUEUES) in _worker_queues(compose)


def test_light_worker_listens_to_the_maintenance_queue():
    assert set(LIGHT_WORKER_QUEUES) in _worker_queues("docker-compose.yml")
