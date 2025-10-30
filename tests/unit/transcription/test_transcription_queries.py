# tests/unit/transcription/test_transcription_queries.py
import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from src.media_processing.transcription.application.queries.transcription_queries import TranscriptionQueries
from src.media_processing.transcription.domain.transcription import Transcription


@pytest.fixture
def mock_transcription_repository():
    return AsyncMock()


@pytest.mark.asyncio
async def test_get_by_id(mock_transcription_repository):
    """Tests retrieving a transcription by its ID."""
    # Arrange
    transcription_id = str(uuid4())
    expected_transcription = Transcription(id=transcription_id, media_id=str(uuid4()))
    mock_transcription_repository.find_by_id.return_value = expected_transcription

    queries = TranscriptionQueries(transcription_repository=mock_transcription_repository)

    # Act
    result = await queries.get_by_id(transcription_id)

    # Assert
    assert result == expected_transcription
    mock_transcription_repository.find_by_id.assert_awaited_once_with(transcription_id)


@pytest.mark.asyncio
async def test_get_by_media_id(mock_transcription_repository):
    """Tests retrieving a transcription by its media ID."""
    # Arrange
    media_id = str(uuid4())
    expected_transcription = Transcription(id=str(uuid4()), media_id=media_id)
    mock_transcription_repository.find_by_media_id.return_value = expected_transcription

    queries = TranscriptionQueries(transcription_repository=mock_transcription_repository)

    # Act
    result = await queries.get_by_media_id(media_id)

    # Assert
    assert result == expected_transcription
    mock_transcription_repository.find_by_media_id.assert_awaited_once_with(media_id)
