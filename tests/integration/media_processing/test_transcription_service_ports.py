from uuid import uuid4

import pytest

from src.media_processing.application.dtos import (
    ReprocessTranscriptionCommand,
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
                "summarization_provider": None,
                "sentiment_provider": None,
                "topic_modeling_provider": None,
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

    def set_context(self, *args, **kwargs):
        return None


class FakeLogger:
    async def log_operation(self, **kwargs):
        return None


@pytest.mark.integration
@pytest.mark.anyio
async def test_reprocess_transcription_emits_completed_event():
    repo = FakeTranscriptionRepo()
    scheduler = FakeScheduler()
    storage = FakeStorage()
    event_bus = FakeEventBus()
    metrics = FakeMetrics()

    service = TranscriptionService(
        transcription_repo=repo,
        task_scheduler=scheduler,
        transcription_logger=FakeLogger(),
        transcription_metrics=metrics,
        storage_service=storage,
        speech_recognizer_factory=lambda provider: FakeRecognizer(),
        media_queries=FakeMediaQueries(),
        event_bus=event_bus,
    )

    command = ReprocessTranscriptionCommand(
        media_id=uuid4(),
        provider=None,
        language="en",
        force=False,
        user_id=uuid4(),
    )

    await service.reprocess_transcription(command)

    # A transcription should be saved and task scheduled
    assert len(repo.saved) == 1
    assert scheduler.last_call is not None
