"""Unit tests for :mod:`src.summarization.application.summarization_service`."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from src.text_analysis.summarization.application.summarization_service import SummarizationService


@pytest.fixture
def repo_mock() -> AsyncMock:
    repo = AsyncMock()
    repo.add = AsyncMock()
    repo.update = AsyncMock()
    repo.get_by_media_id = AsyncMock()
    repo.delete_by_media_id = AsyncMock()
    return repo


@pytest.fixture
def summarizer_mock() -> AsyncMock:
    summarizer = AsyncMock()
    summarizer.summarize = AsyncMock(return_value="Condensed summary")
    return summarizer





@pytest.mark.asyncio
async def test_generate_summary_schedules_background_task(
    repo_mock: AsyncMock,
    summarizer_mock: AsyncMock,
) -> None:
    text_analysis_service_mock = AsyncMock()
    text_analysis_service_mock.schedule_summarization_task = AsyncMock(return_value={"task_id": "task-123"})

    service = SummarizationService(
        summarization_repo=repo_mock,
        summarizer=summarizer_mock,
        text_analysis_service=text_analysis_service_mock,
    )

    media_id = uuid4()
    result = await service.generate_summary(
        media_id=media_id,
        text_content="This is a long form transcript that should be summarised.",
        provider="test",
    )

    text_analysis_service_mock.schedule_summarization_task.assert_awaited_once_with(
        media_id=str(media_id),
        text_content="This is a long form transcript that should be summarised.",
        provider="test",
        options=None,
    )
    assert result["success"] is True
    assert result["media_id"] == str(media_id)
    assert result["task_id"] == "task-123"
    assert "message" in result


@pytest.mark.asyncio
async def test_generate_summary_forwards_options(
    repo_mock: AsyncMock,
    summarizer_mock: AsyncMock,
) -> None:
    text_analysis_service_mock = AsyncMock()
    text_analysis_service_mock.schedule_summarization_task = AsyncMock(return_value={"task_id": "task-123"})

    service = SummarizationService(
        summarization_repo=repo_mock,
        summarizer=summarizer_mock,
        text_analysis_service=text_analysis_service_mock,
    )

    media_id = uuid4()
    options = {"force": True, "max_len": 512}

    result = await service.generate_summary(
        media_id=media_id,
        text_content="New content that replaces the previous version.",
        provider="new",
        options=options,
    )

    text_analysis_service_mock.schedule_summarization_task.assert_awaited_once_with(
        media_id=str(media_id),
        text_content="New content that replaces the previous version.",
        provider="new",
        options=options,
    )
    assert result["success"] is True
    assert result["task_id"] == "task-123"

