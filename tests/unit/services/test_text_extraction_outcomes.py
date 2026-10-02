"""Extração: falhas definitivas visíveis, tempo registrado, mídia excluída ignorada."""
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.media_processing.application.services.text_extraction_service import TextExtractionService
from src.media_processing.domain import Transcription, TranscriptionStatus
from src.media_processing.domain.errors import NoTextFoundError
from src.shared.domain.events import MediaProcessingFailed, TranscriptionCompleted
from tests.mocks.in_memory_event_bus import InMemoryEventBus


class Stats:
    def __init__(self):
        self.calls = []

    async def log_stat(self, *args):
        self.calls.append(args)


def _service(record, text):
    repo = MagicMock()
    repo.get_by_media_id = AsyncMock(return_value=record)
    repo.save = AsyncMock()
    storage = MagicMock()
    async def download_to(path, destination):
        with open(destination, "wb") as target:
            target.write(b"%PDF")
        return True

    storage.download_to = AsyncMock(side_effect=download_to)
    extractor = MagicMock()
    extractor.extract = AsyncMock(return_value=text)
    ocr = MagicMock()
    ocr.extract = AsyncMock(return_value=text)
    bus, stats = InMemoryEventBus(), Stats()
    service = TextExtractionService(
        repository=repo, task_scheduler=None, storage_service=storage,
        text_extractor=extractor, ocr_provider=ocr, event_bus=bus, stats_recorder=stats,
    )
    return service, bus, stats, extractor


def _record():
    return Transcription(media_id=uuid4(), user_id=uuid4(), status=TranscriptionStatus.PENDING, provider="text_extraction")


@pytest.mark.asyncio
async def test_a_file_without_text_fails_for_good_on_the_first_attempt():
    record = _record()
    service, bus, stats, _ = _service(record, "   ")

    with pytest.raises(NoTextFoundError):
        await service.execute_text_extraction(record.media_id, "a.txt", "local", final_attempt=False)

    assert record.status == TranscriptionStatus.FAILED
    [failure] = [e for e in bus.events if isinstance(e, MediaProcessingFailed)]
    assert "Nenhum texto" in failure.error_message
    assert stats.calls[-1][0] == "text_extraction" and stats.calls[-1][-1] == "failed"


@pytest.mark.asyncio
async def test_extraction_time_is_recorded_like_the_transcription():
    record = _record()
    service, bus, stats, _ = _service(record, "Um texto qualquer do documento.")

    await service.execute_text_extraction(record.media_id, "a.txt", "local")

    assert any(isinstance(e, TranscriptionCompleted) for e in bus.events)
    task, seconds, size, media_seconds, provider, status = stats.calls[-1]
    assert (task, provider, status) == ("text_extraction", "text_extractor", "success") and size == 4


@pytest.mark.asyncio
async def test_a_media_deleted_while_queued_is_not_processed():
    service, bus, stats, extractor = _service(None, "texto")

    await service.execute_text_extraction(uuid4(), "a.txt", "local")

    extractor.extract.assert_not_awaited()
    assert not [e for e in bus.events if not type(e).__name__.startswith("MediaProcessingStarted")]
