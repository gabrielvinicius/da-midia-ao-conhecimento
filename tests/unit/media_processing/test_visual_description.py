"""Descrição dos quadros de vídeo, feita no processamento junto com a transcrição."""
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.media_processing.application.services.transcription_service import (
    TranscriptionService,
)
from src.media_processing.application.services.visual_description_service import (
    VisualDescriptionService,
)
from src.media_processing.domain import Transcription
from src.media_processing.domain.visual_sampling import (
    VISUAL_CONTEXT_KEY,
    frame_timestamps,
    is_video_file,
)


def test_frame_timestamps_scale_with_duration():
    assert len(frame_timestamps(60)) == 3       # mínimo
    assert len(frame_timestamps(15 * 60)) == 5  # ~1 a cada 3 min
    assert len(frame_timestamps(3 * 3600)) == 8  # máximo
    ts = frame_timestamps(600)
    assert all(0 < t < 600 for t in ts) and ts == sorted(ts)
    assert frame_timestamps(0) == []


def test_only_video_files_have_frames():
    assert is_video_file("u/2026/10/m/aula.MP4")
    assert not is_video_file("u/2026/10/m/aula.mp3")
    assert not is_video_file("u/2026/10/m/apostila.pdf")
    assert not is_video_file(None)


class _FakeExtractor:
    def __init__(self):
        self.calls = []

    async def extract_frames(self, data, timestamps):
        self.calls.append(len(timestamps))  # o vídeo é gravado uma vez para todos
        return [b"frame"] * len(timestamps)


class _FakeVision:
    model_label = "fake-vision"

    def __init__(self, fail=False):
        self.calls = 0
        self.released = False
        self.fail = fail

    async def describe_frame(self, frame, prompt=""):
        self.calls += 1
        if self.fail:
            raise RuntimeError("sem memória")
        return "Visual description unavailable." if self.calls == 1 else "um slide com um gráfico"

    async def release(self):
        self.released = True


@pytest.mark.asyncio
async def test_describes_frames_skips_failures_and_releases_memory():
    vision, extractor = _FakeVision(), _FakeExtractor()

    context = await VisualDescriptionService(vision, extractor).describe(b"video", 60)

    assert len(context) == 2  # 3 quadros, 1 sem descrição
    assert all("gráfico" in line for line in context)
    assert context[0].startswith("[00:30]")
    assert extractor.calls == [3]
    assert vision.released  # memória devolvida antes da análise


@pytest.mark.asyncio
async def test_vision_failure_does_not_break_processing():
    vision = _FakeVision(fail=True)

    assert await VisualDescriptionService(vision, _FakeExtractor()).describe(b"video", 60) == []
    assert vision.released


def _service(visual):
    repo, storage, recognizer, bus, stats = (AsyncMock() for _ in range(5))
    storage.retrieve.return_value = b"bytes"
    recognizer.transcribe.return_value = {
        "text": "a derivada",
        "segments": [{"text": "a derivada", "start": 0.0, "end": 600.0}],
    }
    service = TranscriptionService(
        transcription_repo=repo,
        task_scheduler=None,
        transcription_logger=AsyncMock(),
        transcription_metrics=AsyncMock(),
        storage_service=storage,
        speech_recognizer_factory=lambda _p: recognizer,
        media_queries=None,
        event_bus=bus,
        stats_recorder=stats,
        visual_describer=visual,
    )
    transcription = Transcription(media_id=uuid4(), provider="whisper")
    repo.get_by_id.return_value = transcription
    return service, transcription, stats


async def _run(service, transcription, file_path):
    return await service.execute_transcription(
        transcription_id=transcription.id,
        media_id=transcription.media_id,
        file_path=file_path,
        storage_provider="local",
        transcription_provider="whisper",
        language="pt",
    )


@pytest.mark.asyncio
async def test_video_descriptions_are_stored_with_the_transcription():
    visual = AsyncMock()
    visual.describe.return_value = ["[05:00] um slide com a regra da cadeia"]
    service, transcription, stats = _service(visual)

    await _run(service, transcription, "u/2026/10/m/aula.mp4")

    visual.describe.assert_awaited_once_with(b"bytes", 600.0)
    # Guardadas no resultado da transcrição, de onde a análise as lê.
    assert transcription.result[VISUAL_CONTEXT_KEY] == ["[05:00] um slide com a regra da cadeia"]
    assert "visual_description" in [c.args[0] for c in stats.log_stat.await_args_list]


@pytest.mark.asyncio
async def test_audio_is_not_sent_to_the_vision_model():
    visual = AsyncMock()
    service, transcription, _ = _service(visual)

    await _run(service, transcription, "u/2026/10/m/aula.mp3")

    visual.describe.assert_not_awaited()
    assert VISUAL_CONTEXT_KEY not in (transcription.result or {})
