"""Unit tests for :mod:`src.summarization.application.summarization_service`."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.summarization.application.summarization_service import SummarizationService
from src.summarization.domain.summary import SummaryStatus


@pytest.fixture
def repo_mock() -> AsyncMock:
    repo = AsyncMock()
    repo.add = AsyncMock(side_effect=lambda summary: summary)
    repo.update = AsyncMock(side_effect=lambda summary: summary)
    repo.get_by_media_id = AsyncMock(return_value=None)
    repo.delete_by_media_id = AsyncMock()
    return repo


@pytest.fixture
def summarizer_mock() -> AsyncMock:
    summarizer = AsyncMock()
    summarizer.summarize = AsyncMock(return_value="Condensed summary")
    return summarizer


@pytest.mark.asyncio
async def test_generate_summary_creates_new_entry(repo_mock: AsyncMock, summarizer_mock: AsyncMock) -> None:
    service = SummarizationService(
        summarization_repo=repo_mock,
        summarizer=summarizer_mock,
    )

    media_id = uuid4()
    result = await service.generate_summary(
        media_id=media_id,
        text_content="This is a long form transcript that should be summarised.",
        provider="test",
    )

    repo_mock.add.assert_awaited()
    repo_mock.update.assert_awaited()
    summarizer_mock.summarize.assert_awaited_once()
    assert result.status is SummaryStatus.COMPLETED
    assert result.text == "Condensed summary"


@pytest.mark.asyncio
async def test_generate_summary_updates_existing(repo_mock: AsyncMock, summarizer_mock: AsyncMock) -> None:
    service = SummarizationService(
        summarization_repo=repo_mock,
        summarizer=summarizer_mock,
    )

    media_id = uuid4()
    existing = await service.generate_summary(
        media_id=media_id,
        text_content="Initial transcript with enough detail to summarise.",
        provider="original",
    )

    repo_mock.get_by_media_id.return_value = existing
    summarizer_mock.summarize.reset_mock()
    summarizer_mock.summarize.return_value = "Updated summary"

    updated = await service.generate_summary(
        media_id=media_id,
        text_content="New content that replaces the previous version.",
        provider="new",
    )

    assert updated.provider == "new"
    assert updated.text == "Updated summary"
    assert summarizer_mock.summarize.await_count == 1


@pytest.mark.asyncio
async def test_mark_failure_records_error(repo_mock: AsyncMock, summarizer_mock: AsyncMock) -> None:
    service = SummarizationService(
        summarization_repo=repo_mock,
        summarizer=summarizer_mock,
    )

    media_id = uuid4()
    failure = await service.mark_failure(media_id=media_id, error_message="Failed", provider="x")

    assert failure.status is SummaryStatus.FAILED
    assert failure.error_message == "Failed"

