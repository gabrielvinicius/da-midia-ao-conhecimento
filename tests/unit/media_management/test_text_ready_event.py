"""A transcrição concluída vira TextContentReady sem perder idioma nem arquivo."""
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.media_management.application.event_handlers import MediaEventHandlers
from src.shared.domain.events import MediaFailed, TextContentReady, TranscriptionCompleted


@pytest.mark.asyncio
async def test_language_and_filename_reach_the_analysis():
    media_service = MagicMock()
    media_service.record_text_ready = AsyncMock(return_value=object())
    bus = AsyncMock()
    handlers = MediaEventHandlers(media_service, bus, retry_delays=(0, 0, 0))
    media_id = str(uuid4())

    await handlers.handle_transcription_completed(
        TranscriptionCompleted(
            media_id=media_id,
            transcription_id=str(uuid4()),
            text="olá",
            user_id=str(uuid4()),
            language="en",
            filename="aula.mp4",
            correlation_id="c1",
        )
    )

    event = bus.publish.await_args.args[0]
    assert isinstance(event, TextContentReady)
    assert (event.media_id, event.language, event.filename, event.correlation_id) == (
        media_id, "en", "aula.mp4", "c1",
    )


def _completed(media_id):
    return TranscriptionCompleted(
        media_id=media_id, transcription_id=str(uuid4()), text="olá", user_id=str(uuid4())
    )


@pytest.mark.asyncio
async def test_a_brief_database_failure_is_retried():
    media_service = MagicMock()
    media_service.record_text_ready = AsyncMock(side_effect=[RuntimeError("banco fora"), object()])
    bus = AsyncMock()
    handlers = MediaEventHandlers(media_service, bus, retry_delays=(0, 0, 0))

    await handlers.handle_transcription_completed(_completed(str(uuid4())))

    assert media_service.record_text_ready.await_count == 2
    assert isinstance(bus.publish.await_args.args[0], TextContentReady)


@pytest.mark.asyncio
async def test_text_not_recorded_fails_the_media_and_warns_the_user():
    media_service = MagicMock()
    media_service.record_text_ready = AsyncMock(side_effect=RuntimeError("banco fora"))
    media_service.record_processing_failed = AsyncMock()
    bus = AsyncMock()
    handlers = MediaEventHandlers(media_service, bus, retry_delays=(0, 0))
    media_id = str(uuid4())

    await handlers.handle_transcription_completed(_completed(media_id))

    assert media_service.record_text_ready.await_count == 3
    media_service.record_processing_failed.assert_awaited_once()
    event = bus.publish.await_args.args[0]
    assert isinstance(event, MediaFailed)
    assert (event.media_id, event.stage) == (media_id, "text_ready")
