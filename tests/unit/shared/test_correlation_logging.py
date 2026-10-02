"""Logs em JSON com o identificador da requisição, da API até as tarefas."""
import io
import json
import logging

import pytest
import structlog
from httpx import ASGITransport, AsyncClient
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from src.celery_app import _bind_task_context, _clear_task_context
from src.shared.infrastructure.middleware.correlation_middleware import (
    CorrelationIdMiddleware,
    correlation_id_of,
)
from src.shared.infrastructure.observability.logging.logging_config import configure_logging, get_logger


def _last_line(buffer: io.StringIO) -> dict:
    return json.loads(buffer.getvalue().strip().splitlines()[-1])


@pytest.fixture
def json_logging():
    configure_logging("test-service", level="INFO", log_format="json")
    buffer = io.StringIO()
    logging.getLogger().handlers[0].setStream(buffer)
    yield buffer
    structlog.contextvars.clear_contextvars()
    configure_logging("test", level="DEBUG", log_format="console")


def test_logs_are_json_and_carry_the_bound_context(json_logging):
    structlog.contextvars.bind_contextvars(correlation_id="abc")
    get_logger("x").info("hello", media_id="m1")

    record = _last_line(json_logging)
    assert record["event"] == "hello"
    assert record["correlation_id"] == "abc"
    assert record["service"] == "test-service"
    assert record["level"] == "info"


def test_json_is_the_default_format(monkeypatch, json_logging):
    monkeypatch.delenv("LOG_FORMAT", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    configure_logging("svc")
    logging.getLogger().handlers[0].setStream(json_logging)
    get_logger("x").info("default")
    assert _last_line(json_logging)["event"] == "default"
    assert logging.getLogger().level == logging.INFO


async def _echo(request: Request):
    return JSONResponse(
        {"state": correlation_id_of(request), "context": structlog.contextvars.get_contextvars()}
    )


@pytest.mark.asyncio
async def test_middleware_binds_the_request_id_to_logs_and_state():
    app = Starlette(routes=[Route("/", _echo)])
    app.add_middleware(CorrelationIdMiddleware)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        given = await client.get("/", headers={"X-Correlation-ID": "req-1"})
        generated = await client.get("/")

    assert given.headers["X-Correlation-ID"] == "req-1"
    assert given.json() == {"state": "req-1", "context": {"correlation_id": "req-1"}}
    new_id = generated.headers["X-Correlation-ID"]
    assert new_id and new_id != "req-1"
    assert generated.json()["context"] == {"correlation_id": new_id}
    # Nada vaza para fora da requisição.
    assert "correlation_id" not in structlog.contextvars.get_contextvars()


def test_task_logs_carry_the_correlation_id_of_the_request():
    task = type("T", (), {"name": "media.transcription"})()
    _bind_task_context(task_id="t-1", task=task, kwargs={"correlation_id": "req-1", "media_id": "m-1"})
    assert structlog.contextvars.get_contextvars() == {
        "task_id": "t-1",
        "task_name": "media.transcription",
        "correlation_id": "req-1",
        "media_id": "m-1",
    }
    _clear_task_context()
    assert structlog.contextvars.get_contextvars() == {}
