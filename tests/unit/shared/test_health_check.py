"""O /health responde 503 quando o banco ou o Redis falham.

Antes respondia 200 com "unhealthy" no corpo, e o healthcheck do Docker
(curl -f) nunca via a API doente.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.shared.infrastructure.observability.health import health_check as health


def _client(monkeypatch, database: bool, redis: bool) -> TestClient:
    async def db():
        return database

    async def rd():
        return redis

    monkeypatch.setattr(health, "CHECKS", {"database": db, "redis": rd})
    app = FastAPI()
    app.include_router(health.router)
    return TestClient(app)


def test_healthy(monkeypatch):
    r = _client(monkeypatch, True, True).get("/health")
    assert r.status_code == 200 and r.json() == {"status": "healthy", "database": "connected", "redis": "connected"}


@pytest.mark.parametrize("database, redis", [(False, True), (True, False)])
def test_any_failure_is_503(monkeypatch, database, redis):
    r = _client(monkeypatch, database, redis).get("/health")
    assert r.status_code == 503 and r.json()["status"] == "unhealthy"
