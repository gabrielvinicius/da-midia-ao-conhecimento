"""Unit tests for :mod:`src.summarization.application.summarization_service`."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.summarization.application.summarization_service import SummarizationService
from src.summarization.domain.summary import Summary


@pytest.fixture
def repo_mock() -> AsyncMock:
    mock = AsyncMock()
    mock.add = AsyncMock()
    mock.update = AsyncMock()
    mock.get_by_media_id = AsyncMock()
    mock.get_by_id = AsyncMock()
    return mock


@pytest.fixture
def scheduler_mock() -> AsyncMock:
    mock = AsyncMock()
    mock.schedule_summarization_task = AsyncMock(return_value={"task_id": "celery-1"})
    return mock


@pytest.fixture
def logger_mock() -> AsyncMock:
    mock = AsyncMock()
    mock.log_operation = AsyncMock()
    return mock


@pytest.fixture
def metrics_mock() -> AsyncMock:
    mock = AsyncMock()
    mock.increment_counter = AsyncMock()
    mock.record_histogram = AsyncMock()
    return mock


@pytest.mark.asyncio
async def test_request_summary_schedules_task(repo_mock: AsyncMock, scheduler_mock: AsyncMock, logger_mock: AsyncMock, metrics_mock: AsyncMock) -> None:
    service = SummarizationService(
        summarization_repo=repo_mock,
        task_scheduler=scheduler_mock,
        summary_logger=logger_mock,
        summary_metrics=metrics_mock,
    )

    result = await service.request_summary("transcription-123", "huggingface")

    repo_mock.add.assert_awaited_once()
    scheduler_mock.schedule_summarization_task.assert_awaited_once()
    logger_mock.log_operation.assert_awaited()
    assert "summary_id" in result
    assert result["task_id"] == "celery-1"


@pytest.mark.asyncio
async def test_process_summary_updates_entity(repo_mock: AsyncMock, scheduler_mock: AsyncMock, logger_mock: AsyncMock, metrics_mock: AsyncMock) -> None:
    service = SummarizationService(
        summarization_repo=repo_mock,
        task_scheduler=scheduler_mock,
        summary_logger=logger_mock,
        summary_metrics=metrics_mock,
    )

    media_id = uuid4()
    summary = Summary.create(media_id=str(media_id), provider="huggingface")
    repo_mock.get_by_media_id.return_value = summary

    processed = await service.process_summary(str(media_id), "huggingface", "Generated text")

    assert processed.status.name == "COMPLETED"
    repo_mock.update.assert_awaited_once_with(summary)


@pytest.mark.asyncio
async def test_process_summary_raises_for_missing_summary(repo_mock: AsyncMock, scheduler_mock: AsyncMock, logger_mock: AsyncMock, metrics_mock: AsyncMock) -> None:
    service = SummarizationService(
        summarization_repo=repo_mock,
        task_scheduler=scheduler_mock,
        summary_logger=logger_mock,
        summary_metrics=metrics_mock,
    )

    repo_mock.get_by_media_id.return_value = None

    with pytest.raises(ValueError):
        await service.process_summary(str(uuid4()), "huggingface", "Generated text")

