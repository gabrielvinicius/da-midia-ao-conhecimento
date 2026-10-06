from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.mark.asyncio
async def test_root_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "Media Processing API"
    assert payload["version"] == "2.0.0"


@pytest.mark.asyncio
async def test_health_check_reports_a_failing_dependency_as_503(monkeypatch):
    from src.shared.infrastructure.observability.health import health_check as health

    async def ok():
        return True

    async def down():
        return False

    monkeypatch.setattr(health, "CHECKS", {"database": ok, "redis": down})
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "unhealthy", "database": "connected", "redis": "disconnected"}


@pytest.mark.asyncio
async def test_metrics_are_not_served_by_the_public_api():
    """As métricas ficam na porta interna (METRICS_PORT), não na API."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/metrics")

    assert response.status_code == 404
