# tests/unit/media_management/test_media_queries.py
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.domain.media import Media, MediaStatus, MediaType


@pytest.fixture
def mock_media_repository():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.list_paginated = AsyncMock()
    return repo


@pytest.mark.asyncio
async def test_get_by_id(mock_media_repository):
    """MediaQueries delegates to repository.get_by_id with UUID input."""
    media_id = uuid4()
    expected_media = Media(
        id=media_id,
        user_id=uuid4(),
        original_file_path="path/to/file.mp4",
        media_type=MediaType.VIDEO,
    )
    mock_media_repository.get_by_id.return_value = expected_media

    queries = MediaQueries(media_repository=mock_media_repository)

    result = await queries.get_by_id(media_id)

    assert result == expected_media
    mock_media_repository.get_by_id.assert_awaited_once_with(media_id)


@pytest.mark.asyncio
async def test_list_all_with_filters(mock_media_repository):
    """list_all forwards pagination and filter arguments to list_paginated."""
    user_id = uuid4()
    expected_media_list = [
        Media(id=uuid4(), user_id=user_id, original_file_path="path/1.mp4", media_type=MediaType.VIDEO),
        Media(
            id=uuid4(),
            user_id=user_id,
            original_file_path="path/2.mp3",
            media_type=MediaType.AUDIO,
            status=MediaStatus.PROCESSING,
        ),
    ]
    mock_media_repository.list_paginated.return_value = expected_media_list

    queries = MediaQueries(media_repository=mock_media_repository)

    page, limit = 2, 5
    status = MediaStatus.PROCESSING
    search = "report"

    result = await queries.list_all(
        page=page,
        limit=limit,
        user_id=user_id,
        status=status,
        search=search,
    )

    assert result == expected_media_list
    mock_media_repository.list_paginated.assert_awaited_once_with(
        page=page,
        limit=limit,
        user_id=user_id,
        status=status,
        search=search,
    )
