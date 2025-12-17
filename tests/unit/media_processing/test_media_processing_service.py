from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.media_processing.application.event_handlers import MediaProcessingEventHandlers
from src.shared.domain.events import MediaUploaded, TextContentReady


@pytest.mark.asyncio
async def test_handle_media_uploaded_dispatches_requests():
    service = AsyncMock()
    handler = MediaProcessingEventHandlers(media_processing_service=service)

    event = MediaUploaded(media_id=str(uuid4()), file_path="/path/to/file", storage_provider="local")

    await handler.handle_media_uploaded(event, context={"file_path": "/path/to/file", "storage_provider": "local"})

    service.request_transcription.assert_awaited()


@pytest.mark.asyncio
async def test_handle_text_content_ready_noops_on_empty():
    service = AsyncMock()
    handler = MediaProcessingEventHandlers(media_processing_service=service)

    event = TextContentReady(media_id=str(uuid4()), text_content="")
    await handler.handle_text_content_ready(event)

    service.request_transcription.assert_not_called()
