from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.media_processing.application.event_handlers import MediaProcessingEventHandlers
from src.shared.domain.events import MediaUploaded, TextContentReady


def _handler():
    return MediaProcessingEventHandlers(
        transcription_service=AsyncMock(),
        text_extraction_service=AsyncMock(),
    )


def _uploaded(media_type):
    return MediaUploaded(
        media_id=str(uuid4()),
        user_id=str(uuid4()),
        media_type=media_type,
        file_path="/path/to/file",
        storage_provider="local",
    )


@pytest.mark.asyncio
async def test_handle_media_uploaded_dispatches_requests():
    handler = _handler()

    await handler.handle_media_uploaded(
        _uploaded(None), context={"file_path": "/path/to/file", "storage_provider": "local"}
    )

    handler._transcription_service.request_transcription_generation.assert_awaited()
    handler._text_extraction_service.request_text_extraction.assert_not_awaited()


@pytest.mark.asyncio
async def test_document_upload_goes_to_text_extraction():
    """O evento traz o valor do enum em minúsculas ("text").

    Antes, o valor era convertido para maiúsculas e não casava com o enum:
    PDFs, DOCX e imagens iam para a transcrição de áudio e falhavam.
    """
    handler = _handler()

    await handler.handle_media_uploaded(_uploaded("text"))

    handler._text_extraction_service.request_text_extraction.assert_awaited_once()
    handler._transcription_service.request_transcription_generation.assert_not_awaited()


@pytest.mark.parametrize("media_type", ["video", "audio", "VIDEO"])
@pytest.mark.asyncio
async def test_audio_and_video_uploads_go_to_transcription(media_type):
    handler = _handler()

    await handler.handle_media_uploaded(_uploaded(media_type))

    handler._transcription_service.request_transcription_generation.assert_awaited_once()
    handler._text_extraction_service.request_text_extraction.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_text_content_ready_noops_on_empty():
    handler = _handler()

    event = TextContentReady(media_id=str(uuid4()), text="")
    await handler.handle_text_content_ready(event)

    # Não deve lançar nem chamar serviços
