"""A transcrição concluída vira TextContentReady sem perder idioma nem arquivo."""
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.media_management.application.event_handlers import MediaEventHandlers
from src.shared.domain.events import TextContentReady, TranscriptionCompleted


@pytest.mark.asyncio
async def test_language_and_filename_reach_the_analysis():
    media_service = MagicMock()
    media_service.record_text_ready = AsyncMock(return_value=object())
    bus = AsyncMock()
    handlers = MediaEventHandlers(media_service, bus)
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
