# tests/unit/media_management/test_media_queries.py
import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.domain.media import Media, MediaType


@pytest.fixture
def mock_media_repository():
    return AsyncMock()


@pytest.mark.asyncio
async def test_get_by_id(mock_media_repository):
    """Tests retrieving a media item by its ID."""
    # Arrange
    media_id = str(uuid4())
    expected_media = Media(id=media_id, user_id=str(uuid4()), original_file_path="path/to/file.mp4", media_type=MediaType.VIDEO)
    mock_media_repository.find_by_id.return_value = expected_media

    queries = MediaQueries(media_repository=mock_media_repository)

    # Act
    result = await queries.get_by_id(media_id)

    # Assert
    assert result == expected_media
    mock_media_repository.find_by_id.assert_awaited_once_with(media_id)


@pytest.mark.asyncio
async def test_list_by_user(mock_media_repository):
    """Tests listing media for a specific user."""
    # Arrange
    user_id = str(uuid4())
    expected_media_list = [
        Media(id=str(uuid4()), user_id=user_id, original_file_path="path/1.mp4", media_type=MediaType.VIDEO),
        Media(id=str(uuid4()), user_id=user_id, original_file_path="path/2.mp3", media_type=MediaType.AUDIO),
    ]
    mock_media_repository.list_by_user.return_value = expected_media_list

    queries = MediaQueries(media_repository=mock_media_repository)

    # Act
    result = await queries.list_by_user(user_id)

    # Assert
    assert result == expected_media_list
    mock_media_repository.list_by_user.assert_awaited_once_with(user_id)
