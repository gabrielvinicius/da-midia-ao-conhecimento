# tests/integration/transcription/test_process_transcription_integration.py
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.domain.media import Media, MediaStatus, MediaType
from src.media_management.infrastructure.media_repository import MediaRepository
from src.media_management.infrastructure.orm.media_entity import MediaEntity
from src.media_processing.transcription.application.commands.process_transcription_command import (
    ProcessTranscriptionCommand,
)
from src.media_processing.transcription.application.commands.process_transcription_command_handler import (
    ProcessTranscriptionCommandHandler,
)
from src.media_processing.transcription.domain.transcription import Transcription
from src.media_processing.transcription.infrastructure.transcription_repository import (
    TranscriptionRepository,
)

pytestmark = pytest.mark.integration

@pytest.mark.asyncio
async def test_process_transcription_handler_persists_results(db_session: AsyncSession):
    """Integration test to verify that the ProcessTranscriptionCommandHandler correctly
    creates a Transcription record and updates the Media status in the database.
    """
    # Arrange: Create a media item in the DB to be processed
    media_repo = MediaRepository(db=db_session)
    media_id = uuid4()
    user_id = uuid4()
    initial_media = Media(
        id=media_id,
        user_id=user_id,
        original_file_path="test/path.mp3",
        media_type=MediaType.AUDIO,
        status=MediaStatus.UPLOADED,
        storage_provider="local"
    )
    await media_repo.save(initial_media)

    # Arrange: Create real repositories and mock external services
    transcription_repo = TranscriptionRepository(db=db_session)
    media_queries = MediaQueries(media_repository=media_repo)

    mock_speech_recognition = AsyncMock()
    mock_speech_recognition.transcribe.return_value = "This is the transcribed text."
    mock_speech_recognition.provider_name = "mock_whisper"

    mock_storage_service = AsyncMock()
    mock_storage_service.download.return_value = (b"fake_audio_bytes", "test.mp3")

    handler = ProcessTranscriptionCommandHandler(
        speech_recognition=mock_speech_recognition,
        storage_service=mock_storage_service,
        event_bus=AsyncMock(),
        transcription_repository=transcription_repo,
        media_queries=media_queries,
        media_repository=media_repo,
        metrics_service=AsyncMock()
    )

    command = ProcessTranscriptionCommand(
        media_id=str(media_id),
        file_path="test/path.mp3",
        storage_provider="local",
        transcription_provider="whisper",
        language="en"
    )

    # Act: Execute the handler
    await handler.handle(command)

    # Assert: Verify the database state directly
    # 1. Check that the Transcription record was created
    transcription_result = await db_session.execute(
        select(Transcription).where(Transcription.media_id == media_id)
    )
    persisted_transcription = transcription_result.scalar_one_or_none()
    assert persisted_transcription is not None
    assert persisted_transcription.text == "This is the transcribed text."

    # 2. Check that the Media status was updated to COMPLETED
    media_result = await db_session.execute(
        select(MediaEntity).where(MediaEntity.id == media_id)
    )
    persisted_media = media_result.scalar_one_or_none()
    assert persisted_media is not None
    assert persisted_media.status == MediaStatus.COMPLETED
