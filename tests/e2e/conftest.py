"""Testes de ponta a ponta: API real contra PostgreSQL e Redis.

Rodam só com E2E=1, DATABASE_URL apontando para um PostgreSQL com as
migrações aplicadas e REDIS_URL para um Redis (é o que a integração
contínua faz). Os modelos de IA não são executados: as tarefas ficam na
fila, sem worker.
"""
import os

import pytest


def pytest_collection_modifyitems(config, items):
    if os.getenv("E2E") == "1":
        return
    skip = pytest.mark.skip(reason="defina E2E=1 com PostgreSQL e Redis disponíveis")
    for item in items:
        if "tests/e2e" in str(item.fspath):
            item.add_marker(skip)
