"""Workers: política de repetição, reanúncio na reentrega, gravação sem fala,
limite de tempo da análise e montagem do barramento de cada processo."""
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from celery.exceptions import Retry, SoftTimeLimitExceeded

from src.media_processing.application.services.text_extraction_service import TextExtractionService
from src.media_processing.application.services.transcription_runner import TranscriptionRunner
from src.media_processing.domain import Transcription, TranscriptionStatus
from src.media_processing.domain.errors import NoSpeechFoundError
from src.shared.domain.errors import NotFoundError, TemporarilyUnavailableError
from src.shared.domain.events import AnalysisFailed, TranscriptionCompleted, TranscriptionFailed
from src.shared.infrastructure.messaging import process_bus
from src.shared.infrastructure.tasks.retry import retry_unless_permanent
from tests.mocks.in_memory_event_bus import InMemoryEventBus


# --- política de repetição -------------------------------------------------

class FakeTask:
    max_retries = 3

    def __init__(self, retries: int) -> None:
        self.request = SimpleNamespace(retries=retries)
        self.countdown = None

    def retry(self, exc, countdown):
        self.countdown = countdown
        return Retry(exc=exc)


@pytest.mark.parametrize("error", [NotFoundError("mídia excluída"), NoSpeechFoundError()])
def test_a_permanent_error_is_not_retried(error):
    task = FakeTask(retries=0)
    retry_unless_permanent(task, error)  # não agenda: quem chamou deixa o erro subir
    assert task.countdown is None


@pytest.mark.parametrize("error", [RuntimeError("CUDA out of memory"), TemporarilyUnavailableError("redis")])
def test_an_error_that_may_pass_is_retried_with_growing_waits(error):
    first, second = FakeTask(retries=0), FakeTask(retries=1)
    with pytest.raises(Retry):
        retry_unless_permanent(first, error)
    with pytest.raises(Retry):
        retry_unless_permanent(second, error)
    assert second.countdown == 2 * first.countdown


def test_the_last_attempt_is_not_retried():
    task = FakeTask(retries=3)
    retry_unless_permanent(task, RuntimeError("falhou de novo"))
    assert task.countdown is None


# --- transcrição -----------------------------------------------------------

def _runner(repo, recognizer, bus):
    storage = AsyncMock()

    async def download_to(_path, destination):
        with open(destination, "wb") as target:
            target.write(b"audio")
        return True

    storage.download_to = AsyncMock(side_effect=download_to)
    return TranscriptionRunner(
        transcription_repo=repo,
        transcription_logger=AsyncMock(),
        transcription_metrics=AsyncMock(),
        storage_service=storage,
        speech_recognizer_factory=lambda _provider: recognizer,
        event_bus=bus,
    )


async def _execute(runner, transcription, final_attempt=False):
    return await runner.execute_transcription(
        transcription_id=transcription.id,
        media_id=transcription.media_id,
        file_path="aula.mp3",
        storage_provider="local",
        transcription_provider="whisper",
        language="pt",
        final_attempt=final_attempt,
    )


@pytest.mark.asyncio
async def test_a_recording_without_speech_fails_at_once_with_the_reason():
    """Antes, a mídia ficava "em análise" sem texto e só falhava horas depois."""
    transcription = Transcription(media_id=uuid4(), provider="whisper")
    repo = AsyncMock()
    repo.get_by_id.return_value = transcription
    recognizer = AsyncMock()
    recognizer.transcribe.return_value = {"text": "   ", "segments": []}
    bus = InMemoryEventBus()

    with pytest.raises(NoSpeechFoundError):
        await _execute(_runner(repo, recognizer, bus), transcription, final_attempt=False)

    [failed] = [e for e in bus.events if isinstance(e, TranscriptionFailed)]
    assert "Nenhuma fala" in failed.error_message
    assert transcription.status == TranscriptionStatus.FAILED


@pytest.mark.asyncio
async def test_a_finished_transcription_delivered_again_is_announced_again_without_the_gpu():
    """O worker caiu entre gravar e anunciar: a mídia não pode ficar parada."""
    transcription = Transcription(media_id=uuid4(), provider="whisper")
    transcription.mark_as_processing()
    transcription.mark_as_completed({"text": "Olá, turma.", "segments": []})
    repo = AsyncMock()
    repo.get_by_id.return_value = transcription
    repo.get_by_media_id.return_value = transcription
    recognizer = AsyncMock()
    bus = InMemoryEventBus()

    await _execute(_runner(repo, recognizer, bus), transcription)

    recognizer.transcribe.assert_not_awaited()
    [completed] = [e for e in bus.events if isinstance(e, TranscriptionCompleted)]
    assert completed.text == "Olá, turma." and completed.transcription_id == str(transcription.id)


@pytest.mark.asyncio
async def test_an_old_message_from_before_a_reprocessing_announces_nothing():
    old = Transcription(media_id=uuid4(), provider="whisper")
    old.mark_as_processing()
    old.mark_as_failed("falhou")
    current = Transcription(media_id=old.media_id, provider="whisper")
    repo = AsyncMock()
    repo.get_by_id.return_value = old
    repo.get_by_media_id.return_value = current
    bus = InMemoryEventBus()

    await _execute(_runner(repo, AsyncMock(), bus), old)

    assert bus.events == []


@pytest.mark.asyncio
async def test_a_finished_extraction_delivered_again_is_announced_again():
    transcription = Transcription(media_id=uuid4(), provider="text_extraction")
    transcription.mark_as_processing()
    transcription.mark_as_extracted("Capítulo 1", "pdf_native")
    repo = AsyncMock()
    repo.get_by_media_id.return_value = transcription
    extractor = AsyncMock()
    bus = InMemoryEventBus()
    service = TextExtractionService(
        repository=repo, task_scheduler=None, storage_service=AsyncMock(),
        text_extractor=extractor, ocr_provider=AsyncMock(), event_bus=bus,
    )

    await service.execute_text_extraction(transcription.media_id, "livro.pdf", "local")

    extractor.extract.assert_not_awaited()
    [completed] = [e for e in bus.events if isinstance(e, TranscriptionCompleted)]
    assert completed.text == "Capítulo 1"


# --- análise ---------------------------------------------------------------

def test_an_analysis_past_its_time_limit_is_announced_as_failed(monkeypatch):
    from src.text_analysis import tasks

    async def analyze(*_args):
        raise SoftTimeLimitExceeded()

    monkeypatch.setattr(tasks, "_analyze", analyze)
    bus = InMemoryEventBus()
    with pytest.raises(SoftTimeLimitExceeded):
        tasks.run_analysis({"media_id": str(uuid4()), "user_id": str(uuid4())}, bus=bus, final_attempt=False)

    [failure] = [e for e in bus.events if isinstance(e, AnalysisFailed)]
    assert failure.error_message == tasks.TIME_LIMIT_MESSAGE


# --- barramento de cada processo ---------------------------------------------

def test_the_process_bus_is_born_with_the_reactions_and_a_failure_reaches_the_task():
    calls = []
    try:
        process_bus.configure_process_subscribers(lambda bus: calls.append(bus))
        bus = process_bus.process_event_bus()
        assert calls == [bus] and process_bus.process_event_bus() is bus  # uma vez por processo

        def broken(_bus):
            raise ImportError("módulo quebrado")

        process_bus.configure_process_subscribers(broken)
        with pytest.raises(ImportError):
            process_bus.process_event_bus()
    finally:
        process_bus.configure_process_subscribers(None)


def test_the_media_state_reacts_before_the_user_is_notified():
    from src.media_management.worker import bind_media_subscribers
    from src.notifications.worker import bind_notification_subscribers
    from src.worker_process import WORKER_SUBSCRIBERS

    order = list(WORKER_SUBSCRIBERS)
    assert order.index(bind_media_subscribers) < order.index(bind_notification_subscribers)
