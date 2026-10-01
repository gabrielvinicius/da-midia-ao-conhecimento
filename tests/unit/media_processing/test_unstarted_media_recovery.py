"""Mídias enviadas sem registro de processamento são reenfileiradas ou dadas como falha."""
import datetime
from unittest.mock import AsyncMock

import pytest

from src.media_processing.application.ports import UnstartedMedia
from src.media_processing.application.services.unstarted_media_recovery import (
    UnstartedMediaRecovery,
)
from src.shared.domain.events import MediaProcessingFailed, MediaUploaded

NOW = datetime.datetime(2026, 10, 1, 12, 0, tzinfo=datetime.timezone.utc)


class _Query:
    def __init__(self, items):
        self.items = items
        self.cutoff = None

    async def list_unstarted(self, uploaded_before):
        self.cutoff = uploaded_before
        return [i for i in self.items if i.uploaded_at.replace(tzinfo=datetime.timezone.utc) < uploaded_before]


def _media(media_id, minutes_ago):
    # Como no banco: UTC sem fuso.
    uploaded = (NOW - datetime.timedelta(minutes=minutes_ago)).replace(tzinfo=None)
    return UnstartedMedia(
        upload=MediaUploaded(media_id=media_id, user_id="u1", media_type="video"),
        uploaded_at=uploaded,
    )


def _recovery(items):
    handler = AsyncMock()
    bus = AsyncMock()
    query = _Query(items)
    recovery = UnstartedMediaRecovery(
        query=query,
        upload_handler=handler,
        event_bus=bus,
        grace_seconds=10 * 60,
        give_up_seconds=60 * 60,
    )
    return recovery, query, handler, bus


@pytest.mark.asyncio
async def test_recent_upload_is_left_alone():
    recovery, query, handler, bus = _recovery([_media("m1", 5)])

    result = await recovery.sweep(NOW)

    assert query.cutoff == NOW - datetime.timedelta(minutes=10)
    assert result.requeued == [] and result.failed == []
    handler.handle_media_uploaded.assert_not_awaited()


@pytest.mark.asyncio
async def test_lost_upload_is_requeued_with_the_original_event():
    item = _media("m1", 15)
    recovery, _, handler, bus = _recovery([item])

    result = await recovery.sweep(NOW)

    assert result.requeued == ["m1"]
    handler.handle_media_uploaded.assert_awaited_once_with(item.upload)
    bus.publish.assert_not_awaited()


@pytest.mark.asyncio
async def test_upload_that_never_starts_is_marked_failed():
    recovery, _, handler, bus = _recovery([_media("m1", 90)])

    result = await recovery.sweep(NOW)

    assert result.failed == ["m1"]
    handler.handle_media_uploaded.assert_not_awaited()
    event = bus.publish.await_args.args[0]
    assert isinstance(event, MediaProcessingFailed)
    assert event.media_id == "m1"
    assert event.metadata["user_id"] == "u1"  # para avisar o usuário
    assert "não chegou a começar" in event.error_message


def test_limits_must_be_ordered():
    with pytest.raises(ValueError):
        UnstartedMediaRecovery(AsyncMock(), AsyncMock(), AsyncMock(), 600, 600)
