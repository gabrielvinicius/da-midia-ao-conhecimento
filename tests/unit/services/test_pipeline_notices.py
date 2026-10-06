"""O módulo de avisos reage aos eventos; a falha de um aviso não sobe a quem publicou."""
from uuid import uuid4

import pytest

from src.notifications import worker as notifications_worker
from src.notifications.application.pipeline_notices import NOTIFIED_EVENTS, notice_for
from src.shared.domain.events import (
    AnalysisCompleted,
    AnalysisFailed,
    MediaProcessingFailed,
    TranscriptionCompleted,
)
from tests.mocks.in_memory_event_bus import InMemoryEventBus


def test_each_event_gets_its_notice():
    user, media = str(uuid4()), str(uuid4())
    done = notice_for(AnalysisCompleted(analysis_id="a", media_id=media, user_id=user, failed_steps=["sentiment"]))
    assert "etapas incompletas (sentiment)" in done.message and done.variables["media_id"] == media

    assert notice_for(AnalysisFailed(media_id=media, user_id=user, error_message="x")).message == "Falha ao analisar o texto."
    assert notice_for(TranscriptionCompleted(media_id=media, user_id=user)).variables["evento"] == "TranscriptionCompleted"
    failed = notice_for(MediaProcessingFailed(media_id=media, user_id=user, stage="text_analysis", error_message="e"))
    assert failed.variables["stage"] == "text_analysis"


def test_events_without_owner_are_not_notified():
    assert notice_for(AnalysisCompleted(analysis_id="a", media_id="m")) is None


@pytest.mark.asyncio
async def test_a_failed_notice_does_not_reach_the_publisher(monkeypatch):
    """Redis fora do ar no aviso: a análise já gravada não pode falhar (nem rodar de novo)."""

    class BrokenSession:
        async def __aenter__(self):
            raise ConnectionError("redis fora do ar")

        async def __aexit__(self, *exc):
            return False

    monkeypatch.setattr(notifications_worker, "AsyncSessionLocal", BrokenSession)
    bus = InMemoryEventBus()
    notifications_worker.bind_notification_subscribers(bus)

    await bus.publish(AnalysisCompleted(analysis_id="a", media_id="m", user_id=str(uuid4())))  # não levanta


def test_notifications_subscribe_to_every_pipeline_outcome():
    bus = InMemoryEventBus()
    notifications_worker.bind_notification_subscribers(bus)
    for event_type in NOTIFIED_EVENTS:
        assert bus._subscriptions[event_type]
