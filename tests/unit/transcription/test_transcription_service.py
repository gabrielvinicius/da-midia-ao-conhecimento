from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.media_processing.transcription.application.transcription_service import (
    TranscriptionService,
)
from src.media_processing.transcription.domain.transcription import (
    Transcription,
    TranscriptionStatus,
)


@pytest.fixture
def service_dependencies():
    repo = AsyncMock()
    scheduler = AsyncMock()
    logger = AsyncMock()
    metrics = AsyncMock()
    storage = AsyncMock()
    recognizer = AsyncMock()
    db_session = AsyncMock()
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
        db_session=db_session,
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
        db_session,
        media_queries,
        event_bus,
    )


@pytest.mark.asyncio
async def test_request_transcription_generation_creates_entity(service_dependencies):
    service, repo, scheduler, metrics, *_ = service_dependencies
    repo.get_by_media_id.return_value = None
    scheduler.schedule_transcription_task.return_value = {"task_id": "task-1"}

    media_id = uuid4()

    result = await service.request_transcription_generation(
        media_id=media_id,
        file_path="/tmp/file.mp3",
        storage_provider="local",
        transcription_provider="whisper",
        language="en",
    )

    repo.add.assert_awaited_once()
    scheduler.schedule_transcription_task.assert_awaited_once()
    metrics.record_operation.assert_awaited_once()
    assert metrics.record_operation.await_args.kwargs["success"] is True
    assert result["task_id"] == "task-1"


@pytest.mark.asyncio
async def test_mark_as_failed(service_dependencies):
    service, repo, *_ = service_dependencies
    transcription = Transcription(media_id=uuid4(), provider="whisper")
    repo.get_by_id.return_value = transcription

    await service.set_speaker_aliases(transcription.id, {"speaker_1": "Alice"})

    repo.update.assert_awaited_once()


@pytest.mark.asyncio
async def test_request_transcription_generation_failure(service_dependencies):
    service, _, scheduler, metrics, *_ = service_dependencies
    scheduler.schedule_transcription_task.side_effect = RuntimeError("error")

    with pytest.raises(RuntimeError):
        await service.request_transcription_generation(
            media_id=uuid4(),
            file_path="/tmp/file.mp3",
            storage_provider="local",
            transcription_provider="whisper",
            language="en",
        )

    metrics.record_operation.assert_awaited_once()
    assert metrics.record_operation.await_args.kwargs["success"] is False


@pytest.mark.asyncio
async def test_process_transcription_job_success(service_dependencies):
    (
        service,
        repo,
        _,
        metrics,
        storage,
        recognizer,
        db_session,
        media_queries,
        event_bus,
    ) = service_dependencies

    media_id = uuid4()
    transcription = Transcription(media_id=media_id, provider="whisper")
    repo.get_by_media_id.return_value = transcription
    storage.download_file.return_value = b"audio-bytes"
    recognizer.transcribe.return_value = {"text": "ok"}
    media_queries.get_by_id.return_value = SimpleNamespace(
        language="pt",
        summarization_provider="huggingface",
        storage_provider="local",
        media_type=SimpleNamespace(value="VIDEO"),
    )

    result = await service.process_transcription_job(
        media_id=media_id,
        file_path="/tmp/file.wav",
        storage_provider="local",
        transcription_provider="whisper",
        language="en",
    )

    assert result == str(transcription.id)
    repo.update.assert_awaited()
    db_session.commit.assert_awaited()
    metrics.record_operation.assert_awaited()
    event_bus.publish.assert_awaited_once()
    published_event = event_bus.publish.await_args.args[0]
    assert published_event.media_id == str(media_id)
    assert published_event.text_content == "ok"


@pytest.mark.asyncio
async def test_process_transcription_job_failure_marks_failed(service_dependencies):
    service, repo, _, metrics, storage, recognizer, db_session, *_ = service_dependencies
    media_id = uuid4()
    transcription = Transcription(media_id=media_id, provider="whisper")
    repo.get_by_media_id.return_value = transcription
    storage.download_file.return_value = b"audio-bytes"
    recognizer.transcribe.side_effect = RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await service.process_transcription_job(
            media_id=media_id,
            file_path="/tmp/file.wav",
            storage_provider="local",
            transcription_provider="whisper",
            language="en",
        )

    assert transcription.status is TranscriptionStatus.FAILED
    repo.update.assert_awaited()
    db_session.commit.assert_awaited()
    metrics.record_operation.assert_awaited()
