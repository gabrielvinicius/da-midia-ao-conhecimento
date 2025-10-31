"""Tests for the transcription event handlers registration."""

import asyncio
import inspect
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from src.media_management.domain.enums import MediaType
from src.shared.events.domain_events import AudioExtracted, MediaDeleted, MediaUploaded
from src.transcription.application.event_handlers import (
    DEFAULT_TRANSCRIPTION_PROVIDER,
    register_event_handlers,
)


def _build_dependencies():
    event_bus = Mock()
    transcription_repository = AsyncMock()
    media_queries = AsyncMock()
    transcription_task = Mock()
    transcription_task.delay = Mock()
    return event_bus, transcription_repository, media_queries, transcription_task


def _extract_handlers(event_bus: Mock):
    return {call.args[0]: call.args[1] for call in event_bus.subscribe.call_args_list}


def _run(coro):
    return asyncio.run(coro)


def test_register_event_handlers_subscribes_coroutine_handlers():
    event_bus, transcription_repository, media_queries, transcription_task = _build_dependencies()

    _run(
        register_event_handlers(
        event_bus,
        transcription_repository,
        media_queries,
        transcription_task=transcription_task,
        )
    )

    handlers = _extract_handlers(event_bus)

    assert {MediaUploaded, AudioExtracted, MediaDeleted} == set(handlers.keys())
    assert all(inspect.iscoroutinefunction(handler) for handler in handlers.values())


def test_media_uploaded_handler_schedules_transcription_task():
    event_bus, transcription_repository, media_queries, transcription_task = _build_dependencies()

    _run(
        register_event_handlers(
        event_bus,
        transcription_repository,
        media_queries,
        transcription_task=transcription_task,
        )
    )

    handlers = _extract_handlers(event_bus)
    media_uploaded_handler = handlers[MediaUploaded]

    media = SimpleNamespace(
        original_file_path="/tmp/original.mp3",
        storage_provider="media-storage",
        transcription_provider=None,
        language="pt",
    )
    media_queries.get_by_id.return_value = media

    event = MediaUploaded(
        media_id="media-1",
        user_id="user-1",
        media_type=MediaType.AUDIO,
        file_path="/ignored/by/handler.mp3",
        storage_provider="event-storage",
    )

    _run(media_uploaded_handler(event))

    media_queries.get_by_id.assert_awaited_once_with(event.media_id)
    transcription_task.delay.assert_called_once_with(
        media_id="media-1",
        file_path="/tmp/original.mp3",
        storage_provider="media-storage",
        transcription_provider=DEFAULT_TRANSCRIPTION_PROVIDER,
        language="pt",
    )


def test_audio_extracted_handler_uses_event_payload_for_task():
    event_bus, transcription_repository, media_queries, transcription_task = _build_dependencies()

    _run(
        register_event_handlers(
        event_bus,
        transcription_repository,
        media_queries,
        transcription_task=transcription_task,
        )
    )

    handlers = _extract_handlers(event_bus)
    audio_extracted_handler = handlers[AudioExtracted]

    media = SimpleNamespace(
        transcription_provider="media-provider",
        storage_provider="media-storage",
        language=None,
    )
    media_queries.get_by_id.return_value = media

    event = AudioExtracted(
        media_id="media-2",
        audio_file_path="/tmp/audio.wav",
        storage_provider="event-storage",
    )

    _run(audio_extracted_handler(event))

    media_queries.get_by_id.assert_awaited_once_with(event.media_id)
    transcription_task.delay.assert_called_once_with(
        media_id="media-2",
        file_path="/tmp/audio.wav",
        storage_provider="event-storage",
        transcription_provider="media-provider",
        language="en",
    )


def test_media_deleted_handler_triggers_repository_cleanup():
    event_bus, transcription_repository, media_queries, transcription_task = _build_dependencies()

    _run(
        register_event_handlers(
        event_bus,
        transcription_repository,
        media_queries,
        transcription_task=transcription_task,
        )
    )

    handlers = _extract_handlers(event_bus)
    media_deleted_handler = handlers[MediaDeleted]

    event = MediaDeleted(media_id="media-3")

    _run(media_deleted_handler(event))

    transcription_repository.delete_by_media_id.assert_awaited_once_with("media-3")

