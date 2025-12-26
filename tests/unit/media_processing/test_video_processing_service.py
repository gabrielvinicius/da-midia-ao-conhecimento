from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.media_processing.application.services.video_processing_service import (
    VideoProcessingService,
)
from src.media_processing.infrastructure.metrics.prometheus_video_processing_metrics import (
    PrometheusVideoProcessingMetrics,
)


@pytest.fixture
def service_dependencies():
    audio_extractor = AsyncMock()
    thumbnail_generator = AsyncMock()
    task_scheduler = AsyncMock()
    storage_service = AsyncMock()
    storage_factory = MagicMock()
    storage_factory.get_download_service.return_value = storage_service
    metrics = AsyncMock(spec=PrometheusVideoProcessingMetrics)

    service = VideoProcessingService(
        video_audio_extractor=audio_extractor,
        video_thumbnail_generator=thumbnail_generator,
        video_processing_task_scheduler=task_scheduler,
        storage_factory=storage_factory,
        default_storage_provider="local",
        video_processing_metrics=metrics,
    )

    return service, audio_extractor, thumbnail_generator, task_scheduler, storage_service, storage_factory, metrics


@pytest.mark.asyncio
async def test_request_video_processing_schedules_task(service_dependencies):
    service, _, _, task_scheduler, *_ = service_dependencies

    task_scheduler.schedule_process_video_task.return_value = {"task_id": "123"}

    media_id = uuid4()
    response = await service.request_video_processing(
        media_id=media_id,
        file_path="/tmp/video.mp4",
        storage_provider="local",
        user_id=None,
        filename=None,
        triggered_by=None,
        actor_id=None,
        correlation_id=None,
    )

    task_scheduler.schedule_process_video_task.assert_awaited_once_with(
        media_id=str(media_id),
        file_path="/tmp/video.mp4",
        storage_provider="local",
        user_id=None,
        filename=None,
        triggered_by=None,
        actor_id=None,
        correlation_id=str(media_id),
    )
    assert response["task_id"] == "123"


@pytest.mark.asyncio
async def test_process_video_job_success(service_dependencies):
    service, audio_extractor, thumbnail_generator, _, storage_service, storage_factory, metrics = service_dependencies

    storage_service.download_file.return_value = b"video-bytes"
    audio_extractor.extract_audio.return_value = {"audio": "ok"}
    thumbnail_generator.generate_thumbnail.return_value = {"thumbnail": "ok"}

    media_id = uuid4()
    result = await service.process_video_job(
        media_id=media_id,
        file_path="/tmp/video.mp4",
        storage_provider="local",
        file_size_bytes=123,
        user_id=None,
        filename=None,
        triggered_by=None,
        actor_id=None,
        correlation_id=None,
    )

    storage_factory.get_download_service.assert_called_once_with("local")
    storage_service.download_file.assert_awaited_once_with("/tmp/video.mp4")
    audio_extractor.extract_audio.assert_awaited_once()
    thumbnail_generator.generate_thumbnail.assert_awaited_once()
    metrics.record_operation.assert_awaited_once()
    assert result["success"] is True


@pytest.mark.asyncio
async def test_process_video_job_failure_raises(service_dependencies):
    service, audio_extractor, _, _, storage_service, storage_factory, metrics = service_dependencies

    storage_service.download_file.return_value = b"video-bytes"
    audio_extractor.extract_audio.side_effect = RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await service.process_video_job(
            media_id=uuid4(),
            file_path="/tmp/video.mp4",
            storage_provider="local",
            user_id=None,
            filename=None,
            triggered_by=None,
            actor_id=None,
            correlation_id=None,
            final_attempt=True,
        )
    metrics.record_operation.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_video_job_failure_intermediate_does_not_publish_failed(monkeypatch, service_dependencies):
    service, audio_extractor, _, _, storage_service, storage_factory, metrics = service_dependencies

    storage_service.download_file.return_value = b"video-bytes"
    audio_extractor.extract_audio.side_effect = RuntimeError("boom")

    published = []

    class DummyBus:
        async def publish(self, event):
            published.append(type(event).__name__)

    service._event_bus = DummyBus()

    with pytest.raises(RuntimeError):
        await service.process_video_job(
            media_id=uuid4(),
            file_path="/tmp/video.mp4",
            storage_provider="local",
            user_id=None,
            filename=None,
            triggered_by=None,
            actor_id=None,
            correlation_id=None,
            final_attempt=False,
        )

    assert "MediaProcessingFailed" not in published
