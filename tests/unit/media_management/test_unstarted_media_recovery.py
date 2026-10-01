"""Mídias enviadas sem registro de processamento são anunciadas de novo ou dadas como falha."""
import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.media_management.application.services.unstarted_media_recovery import (
    UnstartedMediaRecovery,
)
from src.media_management.domain import Media
from src.media_management.domain.enums import MediaType
from src.media_management.domain.enums import MediaStatus
from src.shared.domain.events import MediaFailed, MediaUploaded

NOW = datetime.datetime(2026, 10, 1, 12, 0, tzinfo=datetime.timezone.utc)


def _media(minutes_ago):
    media = Media.create(
        media_id=uuid4(),
        user_id=uuid4(),
        filename="aula.mp4",
        file_size_bytes=10,
        media_type=MediaType.VIDEO,
        storage_provider="local",
        original_file_path="u/2026/10/m/aula.mp4",
    )
    # Como no banco: UTC sem fuso.
    media.created_at = (NOW - datetime.timedelta(minutes=minutes_ago)).replace(tzinfo=None)
    return media


def _recovery(waiting, started=()):
    query, records, bus = AsyncMock(), AsyncMock(), AsyncMock()
    query.list_waiting.return_value = waiting
    records.media_with_processing.return_value = set(started)
    recovery = UnstartedMediaRecovery(query, records, bus, grace_seconds=600, give_up_seconds=3600)
    return recovery, query, bus


@pytest.mark.asyncio
async def test_only_media_older_than_the_grace_period_are_considered():
    recovery, query, bus = _recovery([])

    result = await recovery.sweep(NOW)

    assert query.list_waiting.await_args.args[0] == NOW - datetime.timedelta(minutes=10)
    assert result.requeued == [] and result.failed == []
    bus.publish.assert_not_awaited()


@pytest.mark.asyncio
async def test_media_that_already_has_a_processing_record_is_left_alone():
    media = _media(30)
    recovery, _, bus = _recovery([media], started=[media.id])

    result = await recovery.sweep(NOW)

    assert result.requeued == [] and result.failed == []
    bus.publish.assert_not_awaited()


@pytest.mark.asyncio
async def test_lost_upload_is_announced_again():
    media = _media(15)
    recovery, _, bus = _recovery([media])

    result = await recovery.sweep(NOW)

    assert result.requeued == [str(media.id)]
    event = bus.publish.await_args.args[0]
    assert isinstance(event, MediaUploaded)
    assert event.media_id == str(media.id)
    assert event.file_path == "u/2026/10/m/aula.mp4" and event.media_type == "video"


@pytest.mark.asyncio
async def test_upload_that_never_starts_is_marked_failed():
    media = _media(90)
    recovery, query, bus = _recovery([media])

    result = await recovery.sweep(NOW)

    assert result.failed == [str(media.id)]
    # O módulo de mídias marca a própria mídia e anuncia a falha.
    assert media.status == MediaStatus.FAILED
    assert "não chegou a começar" in media.error_message
    query.update.assert_awaited_once_with(media)
    event = bus.publish.await_args.args[0]
    assert isinstance(event, MediaFailed)
    assert event.user_id == str(media.user_id)  # para avisar o usuário


def test_limits_must_be_ordered():
    with pytest.raises(ValueError):
        UnstartedMediaRecovery(AsyncMock(), AsyncMock(), AsyncMock(), 600, 600)
