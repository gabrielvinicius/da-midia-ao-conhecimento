"""Mídia parada: prazo proporcional à gravação e falha pelo caminho normal."""
import datetime
from uuid import uuid4

import pytest

from src.media_processing.application.services.stalled_processing_monitor import (
    StalledProcessingMonitor,
)
from src.media_processing.domain import Transcription, TranscriptionStatus
from src.media_processing.domain.processing_deadline import (
    MEDIA_DURATION_KEY,
    ProcessingDeadlinePolicy,
)

NOW = datetime.datetime(2026, 9, 30, 12, 0, tzinfo=datetime.timezone.utc)
policy = ProcessingDeadlinePolicy()


def _transcription(status, minutes_ago, media_seconds=None):
    started = NOW - datetime.timedelta(minutes=minutes_ago)
    t = Transcription(media_id=uuid4(), status=status, created_at=started, updated_at=started, provider="fastwhisper")
    if media_seconds:
        t.result = {MEDIA_DURATION_KEY: media_seconds}
    return t


def test_deadline_follows_recording_length_and_measured_speed():
    # Aula de 2 h numa GPU que transcreve em 1/10 do tempo: 12 min esperados,
    # 36 min de prazo.
    assert policy.processing_deadline(7200, 0.1) == pytest.approx(36 * 60)
    # A mesma aula numa CPU (fator 1,5): 3 h × 1,5 × 3 = 13,5 h, limitado a 6 h.
    assert policy.processing_deadline(7200, 1.5) == 6 * 3600


def test_deadline_has_a_floor_and_defaults():
    assert policy.processing_deadline(60, 0.1) == 20 * 60  # áudio curto: mínimo
    assert policy.processing_deadline(None, 0.1) == 60 * 60  # documento/sem duração
    # Sem histórico, supõe o tempo real da gravação: 30 min × 1 × 3 = 90 min.
    assert policy.processing_deadline(1800, None) == 90 * 60


def test_only_attempts_past_the_deadline_are_stalled():
    assert not policy.is_stalled(_transcription(TranscriptionStatus.PROCESSING, 30, 7200), NOW, 0.1)
    assert policy.is_stalled(_transcription(TranscriptionStatus.PROCESSING, 40, 7200), NOW, 0.1)
    # Na fila, espera longa é normal; só um dia parada indica tarefa perdida.
    assert not policy.is_stalled(_transcription(TranscriptionStatus.PENDING, 10 * 60), NOW, 0.1)
    assert policy.is_stalled(_transcription(TranscriptionStatus.PENDING, 25 * 60), NOW, 0.1)
    assert not policy.is_stalled(_transcription(TranscriptionStatus.COMPLETED, 10_000), NOW, 0.1)


class FakeRepo:
    def __init__(self, items):
        self.items = items
        self.asked_before = None

    async def list_unfinished(self, started_before):
        self.asked_before = started_before
        return [t for t in self.items if t.updated_at < started_before]


class FakeService:
    def __init__(self):
        self.calls = []

    async def process_transcription_result(self, *args, **kwargs):
        self.calls.append((args, kwargs))


class FakeFactors:
    async def realtime_factor(self, task_type):
        assert task_type == "transcription"
        return 0.1


class FakeTerminator:
    def __init__(self):
        self.terminated = []

    async def terminate(self, transcription_id, media_id):
        self.terminated.append(media_id)
        return True


@pytest.mark.asyncio
async def test_monitor_fails_stalled_media_through_the_normal_failure_path():
    stuck = _transcription(TranscriptionStatus.PROCESSING, 40, 7200)
    running = _transcription(TranscriptionStatus.PROCESSING, 30, 7200)
    lost_in_queue = _transcription(TranscriptionStatus.PENDING, 25 * 60)
    service, terminator = FakeService(), FakeTerminator()
    monitor = StalledProcessingMonitor(
        FakeRepo([stuck, running, lost_in_queue]), service, policy, FakeFactors(), terminator
    )

    failed = await monitor.sweep(NOW)

    assert set(failed) == {str(stuck.media_id), str(lost_in_queue.media_id)}
    # A tarefa travada é encerrada (libera o worker); a perdida na fila não existe.
    assert terminator.terminated == [str(stuck.media_id)]
    for args, kwargs in service.calls:
        assert kwargs["success"] is False and kwargs["final_attempt"] is True
        assert "Tente novamente" in kwargs["error_message"]
    messages = {args[1]: kwargs["error_message"] for args, kwargs in service.calls}
    assert "36 min" in messages[stuck.media_id]
    assert "fila" in messages[lost_in_queue.media_id]


@pytest.mark.asyncio
async def test_monitor_still_fails_media_when_the_worker_cannot_be_reached():
    class BrokenTerminator:
        async def terminate(self, *_):
            raise TimeoutError("worker não respondeu")

    service = FakeService()
    monitor = StalledProcessingMonitor(
        FakeRepo([_transcription(TranscriptionStatus.PROCESSING, 40, 7200)]),
        service, policy, FakeFactors(), BrokenTerminator(),
    )
    assert len(await monitor.sweep(NOW)) == 1
    assert len(service.calls) == 1


@pytest.mark.asyncio
async def test_duration_probe_returns_none_instead_of_failing(tmp_path):
    from src.media_processing.infrastructure.adapters.video.ffprobe_duration_probe import (
        FfprobeDurationProbe,
    )

    not_media = tmp_path / "nota.txt"
    not_media.write_text("sem áudio")
    assert await FfprobeDurationProbe().duration_seconds(str(not_media)) is None
