"""Origens do CORS vêm do ambiente, sem domínio de exemplo no código."""
from src.shared.infrastructure.config.settings import Settings


def test_cors_origins_come_from_the_environment(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://a.example, https://b.example ,")
    assert Settings().cors_origin_list == ["https://a.example", "https://b.example"]


def test_default_cors_origins_are_only_local(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    origins = Settings().cors_origin_list
    assert origins and all("localhost" in o or "127.0.0.1" in o for o in origins)


def test_api_answers_preflight_only_for_configured_origins():
    from fastapi.testclient import TestClient

    from main import app

    client = TestClient(app)
    headers = {"Access-Control-Request-Method": "GET"}
    allowed = client.options("/", headers={**headers, "Origin": "http://localhost:5173"})
    refused = client.options("/", headers={**headers, "Origin": "https://yourdomain.com"})
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-origin" not in refused.headers
