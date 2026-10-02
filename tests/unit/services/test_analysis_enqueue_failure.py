"""Se a análise não puder ser agendada, a mídia falha de forma visível."""
from contextlib import asynccontextmanager
from uuid import uuid4

import pytest

from src.media_processing import worker as worker_module
from src.shared.domain.events import MediaProcessingFailed, TextContentReady
from tests.mocks.in_memory_event_bus import InMemoryEventBus


class BrokenQueue:
    def request_analysis(self, payload):
        raise ConnectionError("redis fora do ar")


class Handlers:
    async def handle_text_content_ready(self, event):
        return None


@pytest.mark.asyncio
async def test_failed_enqueue_marks_the_media_as_failed(monkeypatch):
    @asynccontextmanager
    async def session():
        yield None

    monkeypatch.setattr(worker_module, "AsyncSessionLocal", session)
    bus = InMemoryEventBus()
    app = worker_module.MediaWorkerApp(event_bus=bus, analysis_requester=BrokenQueue())
    monkeypatch.setattr(app, "_build_media_handlers", lambda _s: Handlers())
    media_id = str(uuid4())

    await app._on_text_content_ready(
        TextContentReady(media_id=media_id, text="texto", user_id=str(uuid4()), correlation_id="req-1")
    )

    [failure] = [e for e in bus.events if isinstance(e, MediaProcessingFailed)]
    assert failure.media_id == media_id and failure.stage == "text_analysis"
    assert failure.correlation_id == "req-1" and "reprocessar" in failure.error_message


def test_sending_a_task_retries_a_short_redis_outage(monkeypatch):
    from src.media_processing.infrastructure.adapters import celery_task_schedulers as schedulers

    sent = {}

    class FakeCelery:
        def send_task(self, name, **kwargs):
            sent.update(kwargs)

    monkeypatch.setattr("src.celery_app.celery", FakeCelery())
    schedulers._send("task", {}, "queue")
    assert sent["retry"] is True and sent["retry_policy"]["max_retries"] >= 3
