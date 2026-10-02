"""Os eventos do processamento conduzem o estado da mídia."""
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.media_management.application.event_handlers import MediaEventHandlers
from src.media_management.application.use_cases import MediaLifecycle
from src.media_management.domain import Media
from src.media_management.domain.enums import MediaStatus, MediaType
from src.shared.domain.events import (
    MediaProcessingFailed,
    MediaProcessingStarted,
    TranscriptionFailed,
)


def _media():
    return Media.create(
        media_id=uuid4(),
        user_id=uuid4(),
        filename="aula.mp4",
        file_size_bytes=10,
        media_type=MediaType.VIDEO,
        storage_provider="local",
        original_file_path="u/aula.mp4",
    )


def _lifecycle(media):
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=media)
    repo.update = AsyncMock()
    return MediaLifecycle(repo), repo


@pytest.mark.asyncio
async def test_started_completed_and_failed_transitions_are_saved():
    media = _media()
    lifecycle, repo = _lifecycle(media)

    await lifecycle.record_processing_started(media.id)
    assert media.status == MediaStatus.PROCESSING

    await lifecycle.record_text_ready(media.id)
    assert media.status == MediaStatus.COMPLETED

    await lifecycle.record_processing_failed(media.id, None)
    assert media.status == MediaStatus.FAILED
    assert media.error_message == "Erro desconhecido"
    assert repo.update.await_count == 3


@pytest.mark.asyncio
async def test_missing_media_is_ignored():
    lifecycle, repo = _lifecycle(None)

    assert await lifecycle.record_processing_started(uuid4()) is None
    repo.update.assert_not_awaited()


def _handlers():
    service = MagicMock()
    for name in ("record_processing_started", "record_text_ready", "record_processing_failed"):
        setattr(service, name, AsyncMock())
    return MediaEventHandlers(service, AsyncMock()), service


@pytest.mark.asyncio
async def test_failure_events_mark_the_media_with_the_message():
    handlers, service = _handlers()
    media_id = uuid4()

    await handlers.handle_transcription_failed(
        TranscriptionFailed(media_id=str(media_id), error_message="sem memória")
    )
    await handlers.handle_media_processing_failed(
        MediaProcessingFailed(media_id=str(media_id), error_message="OCR falhou")
    )

    calls = [c.args for c in service.record_processing_failed.await_args_list]
    assert calls == [(media_id, "sem memória"), (media_id, "OCR falhou")]


@pytest.mark.asyncio
async def test_invalid_media_id_is_logged_not_raised():
    handlers, service = _handlers()

    await handlers.handle_media_processing_started(MediaProcessingStarted(media_id="lixo"))

    service.record_processing_started.assert_not_awaited()


@pytest.mark.asyncio
async def test_a_failing_update_does_not_break_the_event_bus():
    handlers, service = _handlers()
    service.record_processing_started.side_effect = RuntimeError("banco fora")

    # O erro é registrado; o barramento segue para os próximos eventos.
    await handlers.handle_media_processing_started(MediaProcessingStarted(media_id=str(uuid4())))
