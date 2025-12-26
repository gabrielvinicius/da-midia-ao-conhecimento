from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.media_processing.application.event_handlers import MediaProcessingEventHandlers
from src.shared.domain.events import MediaUploaded, TextContentReady


@pytest.mark.asyncio
async def test_handle_media_uploaded_dispatches_requests():
    transcription = AsyncMock()
    text_extraction = AsyncMock()
    video = AsyncMock()

    handler = MediaProcessingEventHandlers(
        transcription_service=transcription,
        text_extraction_service=text_extraction,
        video_processing_service=video,
    )

    event = MediaUploaded(media_id=str(uuid4()), file_path="/path/to/file", storage_provider="local")

    await handler.handle_media_uploaded(event, context={"file_path": "/path/to/file", "storage_provider": "local"})

    transcription.request_transcription_generation.assert_awaited()
    text_extraction.request_text_extraction.assert_not_awaited()
    video.request_video_processing.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_text_content_ready_noops_on_empty():
    handler = MediaProcessingEventHandlers(
        transcription_service=AsyncMock(),
        text_extraction_service=AsyncMock(),
        video_processing_service=AsyncMock(),
    )

    event = TextContentReady(media_id=str(uuid4()), text_content="")
    await handler.handle_text_content_ready(event)

    # Não deve lançar nem chamar serviços
