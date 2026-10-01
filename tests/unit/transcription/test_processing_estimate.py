"""Estimativa a partir da velocidade medida, e nenhuma quando não há base."""
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.media_processing.application.services.transcription_service import (
    TranscriptionService,
)
from src.media_processing.domain import Transcription
from src.media_processing.domain.processing_deadline import expected_processing_seconds


def test_expected_seconds_uses_measured_speed():
    # 1 h de aula; transcrição em 1/10 do tempo e análise em 1/20: 9 min.
    assert expected_processing_seconds(3600, 0.1, 0.05) == pytest.approx(540)
    assert expected_processing_seconds(3600, 0.1) == pytest.approx(360)
    assert expected_processing_seconds(None, 0.1, 0.05) is None  # duração ainda desconhecida
    assert expected_processing_seconds(3600, None, 0.05) is None  # sem histórico


def _service(transcription, factors):
    repo = AsyncMock()
    repo.get_by_media_id.return_value = transcription
    stats = AsyncMock()
    stats.realtime_factor.side_effect = lambda task: factors.get(task)
    return TranscriptionService(
        transcription_repo=repo, task_scheduler=None, transcription_logger=AsyncMock(),
        transcription_metrics=AsyncMock(), storage_service=AsyncMock(),
        speech_recognizer_factory=lambda p: None, media_queries=None, stats_recorder=stats,
    )


@pytest.mark.asyncio
async def test_estimate_for_a_media_being_processed():
    t = Transcription(media_id=uuid4(), result={"media_duration_seconds": 3600})
    service = _service(t, {"transcription": 0.1, "text_analysis": 0.05})
    estimate = await service.estimate_processing(t.media_id)
    assert estimate == {"estimated_seconds": 540, "media_seconds": 3600, "includes_analysis": True}


@pytest.mark.asyncio
async def test_no_estimate_before_the_worker_reads_the_duration():
    service = _service(None, {"transcription": 0.1})
    estimate = await service.estimate_processing(uuid4())
    assert estimate["estimated_seconds"] is None
