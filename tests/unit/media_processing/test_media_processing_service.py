import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from src.media_processing.application.services import MediaProcessingService
from src.shared.events.domain_events import MediaUploaded, TextContentReady


@pytest.fixture
def processing_service():
    transcription_service = AsyncMock()
    transcription_queries = AsyncMock()
    video_service = AsyncMock()
    transcription_metrics = AsyncMock()
    video_metrics = AsyncMock()

    service = MediaProcessingService(
        transcription_service=transcription_service,
        transcription_queries=transcription_queries,
        video_service=video_service,
        transcription_metrics=transcription_metrics,
        video_metrics=video_metrics,
    )

    return (
        service,
        transcription_service,
        video_service,
        transcription_metrics,
        video_metrics,
    )


@pytest.mark.asyncio
async def test_handle_media_uploaded_triggers_transcription_and_video(processing_service):
    (
        service,
        transcription_service,
        video_service,
        transcription_metrics,
        video_metrics,
    ) = processing_service

    event = MediaUploaded(
        media_id=str(uuid4()),
        user_id="user-1",
        filename="/path/to/media.mp4",
        storage_provider="local",
    )

    await service.handle_media_uploaded(
        event,
        context={
            "file_path": "/path/to/media.mp4",
            "storage_provider": "local",
            "transcription_provider": "whisper",
            "language": "pt",
            "file_size_bytes": 12345,
        },
    )

    transcription_service.request_transcription_generation.assert_awaited_once()
    video_service.request_video_processing.assert_awaited_once()
    assert transcription_metrics.record_operation.await_count == 1
    assert video_metrics.record_operation.await_count == 1
    assert video_metrics.record_operation.await_args.kwargs["success"] is True
    assert transcription_metrics.record_operation.await_args.kwargs["success"] is True
    assert video_metrics.record_operation.await_args.kwargs["success"] is True


@pytest.mark.asyncio
async def test_handle_media_uploaded_records_failure(processing_service):
    (
        service,
        transcription_service,
        video_service,
        transcription_metrics,
        video_metrics,
    ) = processing_service

    transcription_service.request_transcription_generation.side_effect = RuntimeError("boom")

    event = MediaUploaded(
        media_id=str(uuid4()),
        user_id="user-1",
        filename="/path/to/media.mp4",
        storage_provider="local",
    )

    await service.handle_media_uploaded(
        event,
        context={
            "file_path": "/path/to/media.mp4",
            "storage_provider": "local",
        },
    )

    transcription_service.request_transcription_generation.assert_awaited_once()
    assert transcription_metrics.record_operation.await_count == 1
    assert transcription_metrics.record_operation.await_args.kwargs["success"] is False
    video_service.request_video_processing.assert_awaited_once()
    assert video_metrics.record_operation.await_count == 1
    assert video_metrics.record_operation.await_args.kwargs["success"] is True


@pytest.mark.asyncio
async def test_handle_text_content_ready_is_noop(processing_service):
    service, *_ = processing_service

    event = TextContentReady(media_id=str(uuid4()))

    await service.handle_text_content_ready(event)
    # No exception thrown and current implementation only logs.
