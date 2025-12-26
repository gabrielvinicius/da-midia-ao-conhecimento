import asyncio

import pytest

from src.text_analysis.infrastructure.adapters.text_generation_ollama_adapter import (
    OllamaTextGenerationAdapter,
)


class DummyResponse:
    def __init__(self, ok: bool, json_data=None, status_code=200):
        self._ok = ok
        self._json = json_data or {"response": "ok"}
        self.status_code = status_code

    def raise_for_status(self):
        if not self._ok:
            raise RuntimeError("fail")

    def json(self):
        return self._json


class DummyAsyncClient:
    def __init__(self, side_effects):
        self.side_effects = iter(side_effects)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, *_, **__):
        return next(self.side_effects)


@pytest.mark.asyncio
async def test_ollama_adapter_retries_success(monkeypatch):
    # First attempt fails, second succeeds
    side_effects = [
        DummyResponse(False),
        DummyResponse(True, {"response": "OK-2"}),
    ]
    monkeypatch.setattr(
        "httpx.AsyncClient",
        lambda timeout: DummyAsyncClient(side_effects),
    )

    adapter = OllamaTextGenerationAdapter(retries=1)
    result = await adapter.summarize_topic("t", "c", [], "pt")
    assert result == "OK-2"
    assert adapter.is_available()


@pytest.mark.asyncio
async def test_ollama_adapter_marks_unavailable_on_failure(monkeypatch):
    side_effects = [DummyResponse(False), DummyResponse(False)]
    monkeypatch.setattr(
        "httpx.AsyncClient",
        lambda timeout: DummyAsyncClient(side_effects),
    )
    adapter = OllamaTextGenerationAdapter(retries=1)
    out = await adapter.summarize_topic("t", "c", [], "pt")
    assert out.startswith("# ")  # fallback markdown
    assert adapter.is_available() is False
