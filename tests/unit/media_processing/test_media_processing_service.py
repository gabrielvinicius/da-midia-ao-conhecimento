import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.media_processing.application.services import MediaProcessingService
from src.shared.events.domain_events import MediaUploaded, TextContentReady


@pytest.fixture
def processing_service():
    transcription_service = AsyncMock()
    transcription_queries = AsyncMock()
    video_service = AsyncMock()

    service = MediaProcessingService(
        transcription_service=transcription_service,
        transcription_queries=transcription_queries,
        video_service=video_service,
    )

    return service, transcription_service, video_service


@pytest.mark.asyncio
async def test_handle_media_uploaded_triggers_transcription_and_video(processing_service):
    service, transcription_service, video_service = processing_service

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
        },
    )

    transcription_service.request_transcription_generation.assert_awaited_once()
    video_service.request_video_processing.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_text_content_ready_is_noop(processing_service):
    service, _, _ = processing_service

    event = TextContentReady(media_id=str(uuid4()))

    await service.handle_text_content_ready(event)
    # No exception thrown and current implementation only logs.
