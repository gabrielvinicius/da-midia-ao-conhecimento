from uuid import uuid4

import pytest

from src.media_processing.application.services.text_extraction_service import (
    TextExtractionService,
)
from src.media_processing.domain import Transcription, TranscriptionStatus
from src.media_processing.infrastructure.adapters.celery_task_schedulers import (
    CeleryTextTaskScheduler,
)
from src.shared.domain.events import MediaProcessingCompleted, TextContentReady


class FakeRepo:
    def __init__(self):
        self.saved = {}

    async def save(self, transcription):
        self.saved[str(transcription.media_id)] = transcription
        return transcription

    async def get_by_media_id(self, media_id):
        return self.saved.get(str(media_id))


class FakeTextExtractor:
    async def extract(self, content: bytes, filename: str):
        return "direct text"


class FakeOCR:
    async def run_ocr(self, content: bytes, filename: str):
        return "ocr text"


class FakeStorage:
    async def download_file(self, path: str):
        return b"file-bytes", "file.txt"

    async def retrieve(self, file_path):
        return b"file-bytes"


class FakeEventBus:
    def __init__(self):
        self.events = []

    async def publish(self, event):
        self.events.append(event)


@pytest.mark.integration
@pytest.mark.anyio
async def test_text_extraction_publishes_events():
    repo = FakeRepo()
    bus = FakeEventBus()

    service = TextExtractionService(
        repository=repo,
        task_scheduler=CeleryTextTaskScheduler(),
        storage_service=FakeStorage(),
        event_bus=bus,
        text_extractor=FakeTextExtractor(),
        ocr_provider=FakeOCR(),
    )

    media_id = uuid4()
    # seed repo entry with a real domain entity
    await repo.save(Transcription(media_id=media_id, status=TranscriptionStatus.PENDING))

    await service.execute_text_extraction(
        media_id=media_id,
        file_path="/fake/file.txt",
        storage_provider="local",
        correlation_id=None,
        user_id=None,
        filename="file.txt",
    )

    assert str(media_id) in repo.saved
    assert any(isinstance(e, MediaProcessingCompleted) for e in bus.events)
    assert any(isinstance(e, TextContentReady) for e in bus.events)
