import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.media_processing.transcription.application.transcription_service import (
    TranscriptionService,
)
from src.media_processing.transcription.domain.transcription import (
    Transcription,
    TranscriptionStatus,
)


@pytest.fixture
def service_dependencies():
    repo = AsyncMock()
    scheduler = AsyncMock()
    logger = MagicMock()
    metrics = MagicMock()
    service = TranscriptionService(
        transcription_repo=repo,
        task_scheduler=scheduler,
        transcription_logger=logger,
        transcription_metrics=metrics,
    )
    return service, repo, scheduler


@pytest.mark.asyncio
async def test_request_transcription_generation_creates_entity(service_dependencies):
    service, repo, scheduler = service_dependencies
    repo.get_by_media_id.return_value = None
    scheduler.schedule_transcription_task.return_value = {"task_id": "task-1"}

    media_id = uuid4()

    result = await service.request_transcription_generation(
        media_id=media_id,
        file_path="/tmp/file.mp3",
        storage_provider="local",
        transcription_provider="whisper",
        language="en",
    )

    repo.add.assert_awaited_once()
    scheduler.schedule_transcription_task.assert_awaited_once()
    assert result["task_id"] == "task-1"


@pytest.mark.asyncio
async def test_mark_as_failed(service_dependencies):
    service, repo, _ = service_dependencies
    transcription = Transcription(media_id=uuid4(), provider="whisper")
    repo.get_by_id.return_value = transcription

    await service.set_speaker_aliases(transcription.id, {"speaker_1": "Alice"})

    repo.update.assert_awaited_once()
