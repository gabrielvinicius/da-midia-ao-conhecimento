import pytest

from uuid import uuid4

from src.media_processing.application.dtos import RequestTranscriptionCommand
from src.media_processing.application.services.transcription_service import (
    TranscriptionService,
)
from src.media_processing.domain import Transcription
from src.media_processing.domain.entities.transcription import TranscriptionStatus
from src.media_processing.application.ports import (
    TranscriptionRepositoryPort,
    TranscriptionTaskSchedulerPort,
    StoragePort,
    OperationLoggerPort,
    MetricsPort,
    SpeechRecognizer,
)


class InMemoryTranscriptionRepo(TranscriptionRepositoryPort):
    def __init__(self):
        self.store = {}

    async def save(self, transcription: Transcription) -> Transcription:
        self.store[transcription.id] = transcription
        return transcription

    async def get_by_id(self, transcription_id):
        return self.store.get(transcription_id)

    async def get_by_media_id(self, media_id):
        for t in self.store.values():
            if t.media_id == media_id:
                return t
        return None


class DummyScheduler(TranscriptionTaskSchedulerPort):
    async def schedule_transcription(self, **kwargs):
        return {"task_id": "dummy"}

    async def schedule_text_extraction(self, **kwargs):
        return {"task_id": "dummy-text"}


class DummyStorage(StoragePort):
    async def retrieve(self, path):
        return b"audio-bytes"


class DummyRecognizer(SpeechRecognizer):
    async def transcribe(self, path: str, language: str):
        return {"text": "hi", "language": language}


class DummyLogger(OperationLoggerPort):
    def info(self, *args, **kwargs):
        return None

    def warning(self, *args, **kwargs):
        return None

    def error(self, *args, **kwargs):
        return None


class DummyMetrics(MetricsPort):
    def record_operation(self, **kwargs):
        return None


@pytest.mark.integration
@pytest.mark.anyio
async def test_transcription_smoke():
    repo = InMemoryTranscriptionRepo()
    recognizer = DummyRecognizer()

    service = TranscriptionService(
        transcription_repo=repo,
        task_scheduler=DummyScheduler(),
        transcription_logger=DummyLogger(),
        transcription_metrics=DummyMetrics(),
        storage_service=DummyStorage(),
        speech_recognizer_factory=lambda provider: recognizer,
        event_bus=None,
    )

    media_id = uuid4()
    transcription_id = uuid4()
    # seed pending transcription
    await repo.save(
        Transcription(
            id=transcription_id,
            media_id=media_id,
            text="",
            provider="dummy",
        )
    )

    await service.process_transcription_result(
        transcription_id,
        media_id,
        {"text": "hi"},
        "dummy",
        success=True,
        correlation_id=str(media_id),
    )

    # process_transcription_result saves into repo
    saved = await repo.get_by_id(transcription_id)
    assert saved is not None
    assert saved.status == TranscriptionStatus.COMPLETED
