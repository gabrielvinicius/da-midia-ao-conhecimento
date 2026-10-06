"""Uma análise por mídia; só erros passageiros são repetidos."""
from uuid import uuid4

import pytest
from sqlalchemy.exc import OperationalError

from src.text_analysis.application.dtos import AnalyzeTextCommand
from src.text_analysis.application.services.text_analysis_service import TextAnalysisService
from src.text_analysis.infrastructure.repositories.inmemory_analysis_repository import (
    InMemoryAnalysisRepository,
)
from src.shared.infrastructure.tasks.retry import is_transient


class NoSteps:
    async def run(self, analysis, on_step_completed=None):
        if on_step_completed:
            await on_step_completed(analysis, "noop")
        return analysis


def _service(repo):
    return TextAnalysisService(repository=repo, pipeline=NoSteps(),)


@pytest.mark.asyncio
async def test_a_new_attempt_overwrites_the_analysis_of_the_same_media():
    repo = InMemoryAnalysisRepository()
    media_id = uuid4()
    command = AnalyzeTextCommand(media_id=media_id, document_id=media_id, text_content="texto")

    first = await _service(repo).analyze_text_content(command)
    second = await _service(repo).analyze_text_content(command)

    assert first["analysis_id"] == second["analysis_id"]
    assert len(repo._store) == 1


def test_only_errors_that_can_pass_by_themselves_are_retried():
    assert is_transient(OperationalError("select", {}, Exception("conexão perdida")))
    assert is_transient(ConnectionError())
    assert not is_transient(TypeError("defeito no código"))
    assert not is_transient(ValueError("dado inválido"))


def test_a_bug_is_reported_at_once_instead_of_rerunning_the_pipeline(monkeypatch):
    """Erro que não passa sozinho: AnalysisFailed já na primeira tentativa."""
    from src.shared.domain.events import AnalysisFailed
    from src.text_analysis import tasks
    from tests.mocks.in_memory_event_bus import InMemoryEventBus

    async def build(**_kwargs):
        return object()

    async def body(*_args):
        raise TypeError("defeito no código")

    monkeypatch.setattr(tasks, "_build_service", build)
    monkeypatch.setattr(tasks, "_async_task_body", body)

    class Session:
        async def __aenter__(self):
            return None

        async def __aexit__(self, *exc):
            return False

    monkeypatch.setattr(tasks, "AsyncSessionLocal", Session)
    bus = InMemoryEventBus()
    with pytest.raises(TypeError):
        tasks._task_body_with_retry_context(
            {"user_id": str(uuid4()), "media_id": str(uuid4()), "correlation_id": "req-2"},
            op_name="t", event_bus=bus, final_attempt=False,
        )
    [failure] = [e for e in bus.events if isinstance(e, AnalysisFailed)]
    assert failure.correlation_id == "req-2" and "defeito" in failure.error_message
    assert TypeError not in tasks.analyze_task.autoretry_for


@pytest.mark.asyncio
async def test_the_request_id_reaches_the_analysis_events():
    from tests.mocks.in_memory_event_bus import InMemoryEventBus

    class WithSummary(NoSteps):
        async def run(self, analysis, on_step_completed=None):
            analysis.summary = "Resumo."
            return analysis

    bus = InMemoryEventBus()
    service = TextAnalysisService(
        repository=InMemoryAnalysisRepository(), pipeline=WithSummary(), event_bus=bus,
    )
    media_id = uuid4()
    await service.analyze_text_content(
        AnalyzeTextCommand(media_id=media_id, document_id=media_id, text_content="t", correlation_id="req-9")
    )
    [completed] = bus.events
    assert type(completed).__name__ == "AnalysisCompleted" and completed.correlation_id == "req-9"
