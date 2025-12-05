from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.media_processing.application.media_processing_service import MediaProcessingService
from src.shared.events.domain_events import MediaUploaded, TextContentReady


@pytest.fixture
def processing_service():
    transcription_service = AsyncMock()
    transcription_queries = AsyncMock()
    video_service = AsyncMock()
    transcription_metrics = AsyncMock()
    video_metrics = AsyncMock()

    service = MediaProcessingService(
        transcription_service=transcription_service,
        transcription_queries=transcription_queries,
        video_service=video_service,
        transcription_metrics=transcription_metrics,
        video_metrics=video_metrics,
    )

    return (
        service,
        transcription_service,
        video_service,
        transcription_metrics,
        video_metrics,
    )


@pytest.mark.asyncio
async def test_handle_media_uploaded_enqueues_tasks(processing_service, monkeypatch):
    (
        service,
        transcription_service,
        video_service,
        transcription_metrics,
        video_metrics,
    ) = processing_service

    from src.media_processing.application import services as services_module

    transcription_delay = MagicMock()
    video_delay = MagicMock()

    monkeypatch.setattr(services_module.process_transcription_task, "delay", transcription_delay)
    monkeypatch.setattr(services_module.process_video_task, "delay", video_delay)

    event = MediaUploaded(
        media_id=str(uuid4()),
        user_id="user-1",
        filename="/path/to/media.mp4",
        storage_provider="local",
    )

    await service.handle_media_uploaded(
        event,
        context={
            "file_path": "/path/to/media.mp4",
            "storage_provider": "local",
            "transcription_provider": "whisper",
            "language": "pt",
            "file_size_bytes": 12345,
        },
    )

    transcription_delay.assert_called_once()
    transcription_kwargs = transcription_delay.call_args.kwargs
    assert transcription_kwargs["media_id"] == event.media_id
    assert transcription_kwargs["file_path"] == "/path/to/media.mp4"
    assert transcription_kwargs["storage_provider"] == "local"
    assert transcription_kwargs["transcription_provider"] == "whisper"
    assert transcription_kwargs["language"] == "pt"
    assert transcription_kwargs["file_size_bytes"] == 12345

    video_delay.assert_called_once()
    video_kwargs = video_delay.call_args.kwargs
    assert video_kwargs["media_id"] == event.media_id
    assert video_kwargs["file_path"] == "/path/to/media.mp4"
    assert video_kwargs["storage_provider"] == "local"
    assert video_kwargs["file_size_bytes"] == 12345
    transcription_service.request_transcription_generation.assert_not_called()
    video_service.request_video_processing.assert_not_called()


@pytest.mark.asyncio
async def test_handle_media_uploaded_swallows_task_errors(processing_service, monkeypatch):
    (
        service,
        transcription_service,
        video_service,
        transcription_metrics,
        video_metrics,
    ) = processing_service

    from src.media_processing.application import services as services_module

    transcription_delay = MagicMock(side_effect=RuntimeError("boom"))
    video_delay = MagicMock()

    monkeypatch.setattr(services_module.process_transcription_task, "delay", transcription_delay)
    monkeypatch.setattr(services_module.process_video_task, "delay", video_delay)

    event = MediaUploaded(
        media_id=str(uuid4()),
        user_id="user-1",
        filename="/path/to/media.mp4",
        storage_provider="local",
    )

    await service.handle_media_uploaded(
        event,
        context={
            "file_path": "/path/to/media.mp4",
            "storage_provider": "local",
        },
    )

    transcription_delay.assert_called_once()
    video_delay.assert_called_once()
    transcription_service.request_transcription_generation.assert_not_called()
    video_service.request_video_processing.assert_not_called()


@pytest.mark.asyncio
async def test_handle_text_content_ready_triggers_analysis(monkeypatch, processing_service):
    service, *_ = processing_service

    calls = {}

    class DummyTask:
        def __call__(self, payload):
            calls["called"] = payload
            return payload

        def delay(self, payload):
            calls["delayed"] = payload
            return payload

    dummy = DummyTask()
    monkeypatch.setattr("src.text_analysis.tasks.analyze_task", dummy)

    event = TextContentReady(
        media_id=str(uuid4()),
        transcription_id=str(uuid4()),
        text_content="hello world",
    )

    await service.handle_text_content_ready(event)

    assert "delayed" in calls or "called" in calls
    payload = calls.get("delayed") or calls.get("called")
    assert payload["media_id"] == event.media_id
    assert payload["transcription_id"] == event.transcription_id
