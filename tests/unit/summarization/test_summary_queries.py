# tests/unit/summarization/test_summary_queries.py
import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from src.text_analysis.summarization.application.queries.summary_queries import SummaryQueries
from src.text_analysis.summarization.domain.summary import Summary


@pytest.fixture
def mock_summary_repository():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.get_by_media_id = AsyncMock()
    return repo


@pytest.mark.asyncio
async def test_get_by_id(mock_summary_repository):
    """Tests retrieving a summary by its ID."""
    # Arrange
    summary_id = str(uuid4())
    expected_summary = Summary.create(media_id=uuid4(), summary_id=summary_id, provider="stub")
    mock_summary_repository.get_by_id.return_value = expected_summary

    queries = SummaryQueries(summary_repository=mock_summary_repository)

    # Act
    result = await queries.get_by_id(summary_id)

    # Assert
    assert result == expected_summary
    mock_summary_repository.get_by_id.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_by_media_id(mock_summary_repository):
    """Tests retrieving a summary by its media ID."""
    # Arrange
    media_id = str(uuid4())
    expected_summary = Summary.create(media_id=media_id, provider="stub")
    mock_summary_repository.get_by_media_id.return_value = expected_summary

    queries = SummaryQueries(summary_repository=mock_summary_repository)

    # Act
    result = await queries.get_by_media_id(media_id)

    # Assert
    assert result == expected_summary
    mock_summary_repository.get_by_media_id.assert_awaited_once()
