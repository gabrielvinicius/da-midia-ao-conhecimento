import asyncio

import pytest

from src.text_analysis.application.ports import TextGenerationUnavailableError

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
    with pytest.raises(TextGenerationUnavailableError):
        await adapter.summarize_topic("t", "c", [], "pt")
    assert adapter.is_available() is False


class RecordingAsyncClient:
    """Registra as requisições e devolve respostas por modelo."""

    def __init__(self, responses_by_model):
        self.responses_by_model = responses_by_model
        self.requests = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, json=None, **__):
        self.requests.append((url, json))
        return self.responses_by_model[json["model"]]


@pytest.mark.asyncio
async def test_ollama_uses_chat_api_with_system_prompt_and_thinking_off(monkeypatch):
    client = RecordingAsyncClient({"qwen3.5:9b": DummyResponse(True, {"message": {"content": " Resumo "}})})
    monkeypatch.setattr("httpx.AsyncClient", lambda timeout: client)

    adapter = OllamaTextGenerationAdapter(model="qwen3.5:9b", host="http://ollama:11434/")
    prompt = "<<<SYSTEM>>>\nSeja fiel.\n<<<END_SYSTEM>>>\nResuma o material."
    out = await adapter.summarize_topic("t", prompt, [], "pt")

    url, body = client.requests[0]
    assert out == "Resumo"
    assert url == "http://ollama:11434/api/chat"
    assert body["think"] is False and body["stream"] is False
    assert body["messages"][0] == {"role": "system", "content": "Seja fiel."}
    assert body["messages"][1] == {"role": "user", "content": "Resuma o material."}
    assert body["options"]["num_ctx"] == 16384  # janela fixa: mudar recarrega o modelo
    assert adapter.last_used_reserve is False


@pytest.mark.asyncio
async def test_ollama_tries_fallback_model_before_giving_up(monkeypatch):
    client = RecordingAsyncClient({
        "qwen3.5:9b": DummyResponse(False),
        "gemma4:e4b": DummyResponse(True, {"message": {"content": "Resumo reserva"}}),
    })
    monkeypatch.setattr("httpx.AsyncClient", lambda timeout: client)

    adapter = OllamaTextGenerationAdapter(model="qwen3.5:9b", fallback_model="gemma4:e4b", retries=0)
    out = await adapter.summarize_topic("t", "texto", [], "pt")

    assert out == "Resumo reserva"
    assert adapter.last_model_used == "gemma4:e4b"
    assert adapter.last_used_reserve is True  # o selo do resumo diz "modelo reserva"
    assert [body["model"] for _, body in client.requests] == ["qwen3.5:9b", "gemma4:e4b"]


@pytest.mark.asyncio
async def test_ollama_raises_when_all_models_fail(monkeypatch):
    """Antes devolvia um texto substituto ("Não informado") que chegava ao
    usuário como se fosse o resumo do modelo reserva."""
    client = RecordingAsyncClient({"qwen3.5:9b": DummyResponse(False)})
    monkeypatch.setattr("httpx.AsyncClient", lambda timeout: client)

    adapter = OllamaTextGenerationAdapter(model="qwen3.5:9b", retries=0)
    with pytest.raises(TextGenerationUnavailableError):
        await adapter.summarize_topic("Tema", "texto", ["a"], "pt")


@pytest.mark.asyncio
async def test_ollama_release_unloads_models(monkeypatch):
    client = RecordingAsyncClient({"qwen3.5:9b": DummyResponse(True, {}), "gemma4:e4b": DummyResponse(True, {})})
    monkeypatch.setattr("httpx.AsyncClient", lambda timeout: client)

    adapter = OllamaTextGenerationAdapter(model="qwen3.5:9b", fallback_model="gemma4:e4b")
    await adapter.release()

    assert [(url.rsplit("/", 1)[-1], body) for url, body in client.requests] == [
        ("generate", {"model": "qwen3.5:9b", "keep_alive": 0}),
        ("generate", {"model": "gemma4:e4b", "keep_alive": 0}),
    ]
