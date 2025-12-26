from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.media_processing.application.dtos import RequestTranscriptionCommand
from src.media_processing.application.services.transcription_service import (
    TranscriptionService,
)
from src.media_processing.domain import Transcription, TranscriptionStatus
from src.shared.domain.events import TranscriptionFailed


@pytest.fixture
def service_dependencies():
    repo = AsyncMock()
    scheduler = AsyncMock()
    logger = AsyncMock()
    metrics = AsyncMock()
    storage = AsyncMock()
    recognizer = AsyncMock()
    media_queries = AsyncMock()
    event_bus = AsyncMock()

    def recognizer_factory(_provider: str):
        return recognizer

    service = TranscriptionService(
        transcription_repo=repo,
        task_scheduler=scheduler,
        transcription_logger=logger,
        transcription_metrics=metrics,
        storage_service=storage,
        speech_recognizer_factory=recognizer_factory,
        media_queries=media_queries,
        event_bus=event_bus,
    )
    return (
        service,
        repo,
        scheduler,
        metrics,
        storage,
        recognizer,
        media_queries,
        event_bus,
    )


@pytest.mark.asyncio
async def test_request_transcription_generation_creates_entity(service_dependencies):
    service, repo, scheduler, metrics, *_ = service_dependencies
    repo.save.return_value = SimpleNamespace(id=uuid4())
    scheduler.schedule_transcription.return_value = {"task_id": "task-1"}

    media_id = uuid4()
    command = RequestTranscriptionCommand(
        media_id=media_id,
        file_path="/tmp/file.mp3",
        storage_provider="local",
        transcription_provider="whisper",
        language="en",
    )

    result = await service.request_transcription_generation(command)

    repo.save.assert_awaited_once()
    scheduler.schedule_transcription.assert_awaited_once()
    metrics.record_operation.assert_awaited_once()
    assert result["task_id"] == "task-1"


@pytest.mark.asyncio
async def test_execute_transcription_success(service_dependencies):
    (
        service,
        repo,
        _,
        metrics,
        storage,
        recognizer,
        media_queries,
        event_bus,
    ) = service_dependencies

    media_id = uuid4()
    transcription_id = uuid4()
    transcription = Transcription(media_id=media_id, provider="whisper")
    repo.get_by_id.return_value = transcription

    storage.retrieve.return_value = b"audio-bytes"
    recognizer.transcribe.return_value = {"text": "ok"}

    result = await service.execute_transcription(
        transcription_id=transcription_id,
        media_id=media_id,
        file_path="/tmp/file.wav",
        storage_provider="local",
        transcription_provider="whisper",
        language="en",
    )

    assert result["text"] == "ok"
    repo.save.assert_awaited()
    # metrics.record_operation.assert_awaited() # verify if execute calls metric
    event_bus.publish.assert_awaited()
    # Verify TranscriptionCompleted was published
    call_args = event_bus.publish.call_args_list
    assert len(call_args) >= 2 # Started + Completed


@pytest.mark.asyncio
async def test_execute_transcription_failure_intermediate_does_not_publish_failed(
    service_dependencies,
):
    (
        service,
        repo,
        _,
        _metrics,
        storage,
        recognizer,
        _media_queries,
        event_bus,
    ) = service_dependencies

    media_id = uuid4()
    transcription_id = uuid4()
    transcription = Transcription(media_id=media_id, provider="whisper")
    repo.get_by_id.return_value = transcription

    storage.retrieve.return_value = b"audio-bytes"
    recognizer.transcribe.side_effect = RuntimeError("falha transitória")

    with pytest.raises(RuntimeError):
        await service.execute_transcription(
            transcription_id=transcription_id,
            media_id=media_id,
            file_path="/tmp/file.wav",
            storage_provider="local",
            transcription_provider="whisper",
            language="en",
            final_attempt=False,
        )

    assert transcription.status == TranscriptionStatus.PROCESSING
    published = [c.args[0] for c in event_bus.publish.call_args_list]
    assert not any(isinstance(e, TranscriptionFailed) for e in published)


@pytest.mark.asyncio
async def test_execute_transcription_failure_final_publishes_failed(service_dependencies):
    (
        service,
        repo,
        _,
        _metrics,
        storage,
        recognizer,
        _media_queries,
        event_bus,
    ) = service_dependencies

    media_id = uuid4()
    transcription_id = uuid4()
    transcription = Transcription(media_id=media_id, provider="whisper")
    repo.get_by_id.return_value = transcription

    storage.retrieve.return_value = b"audio-bytes"
    recognizer.transcribe.side_effect = RuntimeError("falha permanente")

    with pytest.raises(RuntimeError):
        await service.execute_transcription(
            transcription_id=transcription_id,
            media_id=media_id,
            file_path="/tmp/file.wav",
            storage_provider="local",
            transcription_provider="whisper",
            language="en",
            final_attempt=True,
        )

    assert transcription.status == TranscriptionStatus.FAILED
    published = [c.args[0] for c in event_bus.publish.call_args_list]
    assert any(isinstance(e, TranscriptionFailed) for e in published)
