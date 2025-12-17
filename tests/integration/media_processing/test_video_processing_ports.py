from uuid import uuid4

import pytest

from src.media_processing.application.services.video_processing_service import (
    VideoProcessingService,
)
from src.shared.domain.events import MediaProcessingCompleted


class FakeAudioExtractor:
    async def extract_audio(self, video_data: bytes, filename: str, output_format: str):
        return {"success": True, "audio_file_path": "/fake/audio.wav"}


class FakeThumbnailGenerator:
    async def generate_thumbnail(self, video_data: bytes, filename: str, size: str, timestamp: float):
        return {"success": True, "thumbnail_path": "/fake/thumb.jpg"}


class FakeScheduler:
    async def schedule_process_video_task(self, **kwargs):
        return {"task_id": "fake"}


class FakeStorageFactory:
    def __init__(self):
        self.downloaded = []

    def get_download_service(self, provider: str):
        return self

    async def download_file(self, path: str):
        self.downloaded.append(path)
        return b"video-bytes"


class FakeEventBus:
    def __init__(self):
        self.events = []

    async def publish(self, event):
        self.events.append(event)


class FakeMetrics:
    async def record_operation(self, **kwargs):
        return None

    def set_context(self, *args, **kwargs):
        return None


@pytest.mark.integration
@pytest.mark.anyio
async def test_process_video_job_publishes_completion():
    storage = FakeStorageFactory()
    bus = FakeEventBus()
    metrics = FakeMetrics()
    user_id = str(uuid4())

    service = VideoProcessingService(
        video_audio_extractor=FakeAudioExtractor(),
        video_thumbnail_generator=FakeThumbnailGenerator(),
        video_processing_task_scheduler=FakeScheduler(),
        storage_factory=storage,
        video_processing_metrics=metrics,
        event_bus=bus,
    )

    await service.process_video_job(
        media_id=uuid4(),
        file_path="/fake/video.mp4",
        storage_provider="local",
        file_size_bytes=10,
        filename="video.mp4",
        user_id=user_id,
        triggered_by="system",
        actor_id="worker-1",
        correlation_id="corr-123",
    )

    assert any(
        isinstance(e, MediaProcessingCompleted)
        and e.stage == "audio_extraction"
        and e.metadata.get("triggered_by") == "system"
        and e.metadata.get("actor_id") == "worker-1"
        and e.metadata.get("user_id") == user_id
        and e.correlation_id == "corr-123"
        for e in bus.events
    )
    assert storage.downloaded == ["/fake/video.mp4"]
