"""Tests for the refactored AnalyzeSentimentCommandHandler."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.media_processing.transcription.domain.transcription import TranscriptionStatus
from src.shared.events.domain_events import SentimentAnalysisCompleted
from src.shared.exceptions.domain_exceptions import ValidationError
from src.text_analysis.sentiment_analysis.application.commands.analyze_sentiment_command import (
    AnalyzeSentimentCommand,
)
from src.text_analysis.sentiment_analysis.application.commands.analyze_sentiment_command_handler import (
    AnalyzeSentimentCommandHandler,
)
from src.text_analysis.sentiment_analysis.domain.sentiment_analysis import (
    SentimentAnalysis,
)


def _build_handler(
    *,
    sentiment_service: AsyncMock | None = None,
    analysis_repository: AsyncMock | None = None,
    transcription_queries: AsyncMock | None = None,
    connection_manager: AsyncMock | None = None,
    metrics_service: MagicMock | None = None,
) -> AnalyzeSentimentCommandHandler:
    sentiment_service = sentiment_service or AsyncMock()
    analysis_repository = analysis_repository or AsyncMock()
    transcription_queries = transcription_queries or AsyncMock()
    connection_manager = connection_manager or AsyncMock()
    metrics_service = metrics_service or MagicMock()

    return AnalyzeSentimentCommandHandler(
        sentiment_service=sentiment_service,
        analysis_repository=analysis_repository,
        transcription_queries=transcription_queries,
        connection_manager=connection_manager,
        metrics_service=metrics_service,
    )

def _make_transcription(text: str, *, status: TranscriptionStatus = TranscriptionStatus.COMPLETED):
    return type(
        "StubTranscription",
        (),
        {
            "id": "transcription_123",
            "media_id": uuid4(),
            "text": text,
            "status": status,
        },
    )()


@pytest.mark.asyncio
async def test_handle_saves_analysis(mock_metrics_service):
    sentiment_service = AsyncMock()
    payload = {
        "overall_sentiment": "positive",
        "sentiment_score": 0.42,
        "confidence": 0.88,
        "emotions": {"joy": 0.76},
        "sentence_sentiments": [],
        "processing_time": 1.3,
    }
    sentiment_service.analyze_sentiment.return_value = payload

    saved_entities: list[SentimentAnalysis] = []

    async def save(entity: SentimentAnalysis) -> SentimentAnalysis:
        saved_entities.append(entity)
        return entity

    analysis_repository = AsyncMock()
    analysis_repository.find_by_transcription_id = AsyncMock(return_value=None)
    analysis_repository.save = AsyncMock(side_effect=save)

    transcription_queries = AsyncMock()
    transcription_queries.get_by_id = AsyncMock(
        return_value=_make_transcription("The service is fantastic and the staff were helpful.")
    )

    handler = _build_handler(
        sentiment_service=sentiment_service,
        analysis_repository=analysis_repository,
        transcription_queries=transcription_queries,
        connection_manager=AsyncMock(),
        metrics_service=mock_metrics_service,
    )

    command = AnalyzeSentimentCommand(
        transcription_id="transcription_123",
        provider="transformers",
        model="distilbert-base-uncased",
    )

    result = await handler.handle(command)

    assert result.overall_sentiment == "positive"
    assert result.sentiment_score == pytest.approx(0.42)
    assert saved_entities and saved_entities[0] is result


@pytest.mark.asyncio
async def test_handle_returns_cached_result():
    cached = SentimentAnalysis(
        id=str(uuid4()),
        transcription_id="transcription_123",
        media_id=str(uuid4()),
        overall_sentiment="neutral",
        sentiment_score=0.1,
    )

    analysis_repository = AsyncMock()
    analysis_repository.find_by_transcription_id = AsyncMock(return_value=cached)
    sentiment_service = AsyncMock()

    transcription_queries = AsyncMock()
    transcription_queries.get_by_id = AsyncMock(
        return_value=_make_transcription("Cached content should be reused.")
    )

    handler = _build_handler(
        sentiment_service=sentiment_service,
        analysis_repository=analysis_repository,
        transcription_queries=transcription_queries,
    )

    command = AnalyzeSentimentCommand(
        transcription_id="transcription_123",
        provider="transformers",
        model="distilbert-base-uncased",
    )

    result = await handler.handle(command)

    sentiment_service.analyze_sentiment.assert_not_called()
    assert result is cached


@pytest.mark.asyncio
async def test_handle_raises_when_transcription_missing():
    analysis_repository = AsyncMock()
    analysis_repository.find_by_transcription_id = AsyncMock(return_value=None)

    transcription_queries = AsyncMock()
    transcription_queries.get_by_id = AsyncMock(return_value=None)

    handler = _build_handler(
        analysis_repository=analysis_repository,
        transcription_queries=transcription_queries,
    )

    command = AnalyzeSentimentCommand(
        transcription_id="missing",
        provider="transformers",
        model="distilbert-base-uncased",
    )

    with pytest.raises(ValidationError):
        await handler.handle(command)


@pytest.mark.asyncio
async def test_handle_rejects_short_transcription():
    analysis_repository = AsyncMock()
    analysis_repository.find_by_transcription_id = AsyncMock(return_value=None)

    transcription_queries = AsyncMock()
    transcription_queries.get_by_id = AsyncMock(
        return_value=_make_transcription("short")
    )

    handler = _build_handler(
        analysis_repository=analysis_repository,
        transcription_queries=transcription_queries,
    )

    command = AnalyzeSentimentCommand(
        transcription_id="transcription_123",
        provider="transformers",
        model="distilbert-base-uncased",
    )

    with pytest.raises(ValidationError):
        await handler.handle(command)
