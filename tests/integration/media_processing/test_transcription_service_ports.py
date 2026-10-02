from uuid import uuid4

import pytest

from src.media_processing.application.dtos import (
    RequestTranscriptionCommand,
)
from src.media_processing.application.services.transcription_service import (
    TranscriptionService,
)


class FakeTranscriptionRepo:
    def __init__(self):
        self.saved = {}

    async def save(self, transcription):
        self.saved[str(transcription.id)] = transcription
        return transcription

    async def get_by_media_id(self, media_id):
        # not used in this test
        return None


class FakeScheduler:
    def __init__(self):
        self.last_call = None

    async def schedule_transcription(self, **kwargs):
        self.last_call = kwargs
        return {"task_id": "fake"}


class FakeRecognizer:
    provider_name = "fake_whisper"

    async def transcribe(self, audio_bytes, language="auto"):
        return {"text": "hello world", "confidence": 0.9, "duration": 1.0}


class FakeStorage:
    async def download_file(self, path):
        return b"audio-bytes", "audio.wav"


class FakeMediaQueries:
    async def get_media(self, query):
        return type(
            "MediaStub",
            (),
            {
                "id": query.media_id,
                "original_file_path": "/fake/path.wav",
                "storage_provider": "local",
                "transcription_provider": "fake_whisper",
                "language": "en",
                "file_size": 123,
            },
        )()


class FakeEventBus:
    def __init__(self):
        self.events = []

    async def publish(self, event):
        self.events.append(event)


class FakeMetrics:
    def __init__(self):
        self.calls = []

    async def record_operation(self, **kwargs):
        self.calls.append(kwargs)
        return None


class FakeLogger:
    async def log_operation(self, **kwargs):
        return None


@pytest.mark.integration
@pytest.mark.anyio
async def test_request_transcription_saves_and_schedules():
    repo = FakeTranscriptionRepo()
    scheduler = FakeScheduler()
    metrics = FakeMetrics()

    service = TranscriptionService(
        transcription_repo=repo,
        task_scheduler=scheduler,
        transcription_logger=FakeLogger(),
        transcription_metrics=metrics,
    )

    command = RequestTranscriptionCommand(
        media_id=uuid4(),
        file_path="/fake/path.wav",
        storage_provider="local",
        transcription_provider="fake_whisper",
        language="en",
        file_size_bytes=123,
    )

    await service.request_transcription_generation(command)

    # A transcription should be saved and task scheduled
    assert len(repo.saved) == 1
    assert scheduler.last_call is not None
