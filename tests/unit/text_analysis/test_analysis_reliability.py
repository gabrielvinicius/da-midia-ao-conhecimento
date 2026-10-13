from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.shared.domain.errors import NotFoundError, TemporarilyUnavailableError
from src.text_analysis.application.dtos import AnalyzeTextCommand
from src.text_analysis.application.mappers import (
    analysis_diagnostics,
    restore_from_diagnostics,
)
from src.text_analysis.application.pipeline.base import AnalysisPipeline, AnalysisStep
from src.text_analysis.application.ports.transcription_port import TextSourceData
from src.text_analysis.application.services.text_analysis_service import (
    TextAnalysisService,
)
from src.text_analysis.domain import Analysis, Document, Topic
from src.text_analysis.domain.entities.analysis import (
    AnalysisReviewedError,
    AnalysisSourceChangedError,
)
from src.text_analysis.infrastructure.repositories.inmemory_analysis_repository import (
    InMemoryAnalysisRepository,
)


class SummaryStep(AnalysisStep):
    name = "synthesis"
    required = True

    async def process(self, analysis):
        analysis.summary = "Resumo gerado."
        return analysis


class SnapshotRepository(InMemoryAnalysisRepository):
    def __init__(self):
        super().__init__()
        self.snapshots = []

    async def save(self, analysis):
        self.snapshots.append(deepcopy(analysis))
        return await super().save(deepcopy(analysis))


def command(media_id=None, **values):
    media_id = media_id or uuid4()
    return AnalyzeTextCommand(
        media_id=media_id, document_id=media_id, text_content="texto", **values
    )


@pytest.mark.asyncio
async def test_persisted_text_segments_and_identifier_form_one_source():
    request = command()
    source = TextSourceData(
        id=uuid4(),
        media_id=request.media_id,
        text="Texto corrigido.",
        language="es",
        segments=[{"text": "Texto corrigido.", "start": 0, "end": 3}],
        visual_context=["[00:01] slide"],
    )
    sources = AsyncMock()
    sources.get_text_source.return_value = source
    sources.get_media_info.return_value = {}
    pipeline = AsyncMock()
    pipeline.run.side_effect = lambda analysis, **kwargs: analysis
    await TextAnalysisService(
        repository=InMemoryAnalysisRepository(),
        pipeline=pipeline,
        transcription_queries=sources,
    ).analyze_text_content(request)

    analysis = pipeline.run.call_args.args[0]
    assert (analysis.document.text, analysis.document.segments) == (
        source.text,
        source.segments,
    )
    assert analysis.transcription_id == source.id
    assert (analysis.language, analysis.visual_context) == (
        source.language,
        source.visual_context,
    )


@pytest.mark.asyncio
async def test_a_replaced_transcription_request_cannot_analyze_the_new_source():
    request = command(transcription_id=uuid4())
    sources, pipeline = AsyncMock(), AsyncMock()
    sources.get_text_source.return_value = TextSourceData(
        id=uuid4(),
        text="nova transcrição",
        language="pt",
        segments=[],
        media_id=request.media_id,
    )
    repository = SnapshotRepository()
    with pytest.raises(AnalysisSourceChangedError):
        await TextAnalysisService(
            repository=repository,
            pipeline=pipeline,
            transcription_queries=sources,
        ).analyze_text_content(request)
    pipeline.run.assert_not_awaited()
    assert repository.snapshots == []


@pytest.mark.asyncio
async def test_a_missing_source_does_not_fall_back_to_old_queued_text():
    sources, pipeline = AsyncMock(), AsyncMock()
    sources.get_text_source.return_value = None
    repository = SnapshotRepository()
    with pytest.raises(NotFoundError):
        await TextAnalysisService(
            repository=repository,
            pipeline=pipeline,
            transcription_queries=sources,
        ).analyze_text_content(command())
    pipeline.run.assert_not_awaited()
    assert repository.snapshots == []


@pytest.mark.asyncio
@pytest.mark.parametrize("revision", ["summary", "topic", "chapters", "questions"])
async def test_a_worker_cannot_replace_a_reviewed_analysis(revision):
    request = command()
    existing = Analysis.new(Document.from_payload("texto"), media_id=request.media_id)
    existing.summary = "Resumo revisado."
    if revision == "topic":
        existing.topics = [
            Topic(id=0, keywords=[], title="Tema revisado", original_title="Tema da IA")
        ]
    else:
        field = {
            "summary": "original_ai_summary",
            "chapters": "original_ai_chapters",
            "questions": "original_ai_review_questions",
        }[revision]
        existing.diagnostics[field] = [] if revision != "summary" else "Resumo da IA."
    repository = SnapshotRepository()
    await repository.save(existing)
    pipeline = AsyncMock()

    with pytest.raises(AnalysisReviewedError):
        await TextAnalysisService(
            repository=repository, pipeline=pipeline
        ).analyze_text_content(request)

    pipeline.run.assert_not_awaited()
    assert len(repository.snapshots) == 1
    assert (await repository.get(str(existing.id))).summary == "Resumo revisado."


@pytest.mark.asyncio
async def test_a_revision_made_while_the_pipeline_runs_is_not_overwritten():
    repository = SnapshotRepository()
    request = command()
    existing = Analysis.new(Document.from_payload("texto"), media_id=request.media_id)
    existing.summary = "Resumo da IA."
    await repository.save(existing)

    class ConcurrentRevision(SummaryStep):
        async def process(self, analysis):
            await repository.update_summary(
                str(analysis.id), "Correção durante a execução."
            )
            return await super().process(analysis)

    with pytest.raises(AnalysisReviewedError):
        await TextAnalysisService(
            repository=repository,
            pipeline=AnalysisPipeline([ConcurrentRevision()]),
        ).analyze_text_content(request)

    kept = await repository.get(str(existing.id))
    assert kept.summary == "Correção durante a execução."
    assert kept.diagnostics["original_ai_summary"] == "Resumo da IA."


@pytest.mark.asyncio
async def test_completion_is_persisted_only_after_the_pipeline_and_survives_lost_announcement():
    repository, bus = SnapshotRepository(), AsyncMock()
    bus.publish.side_effect = ConnectionError("evento perdido")
    request = command()
    result = await TextAnalysisService(
        repository=repository,
        pipeline=AnalysisPipeline([SummaryStep()]),
        event_bus=bus,
    ).analyze_text_content(request)

    assert [snapshot.pipeline_completed for snapshot in repository.snapshots] == [
        False,
        True,
    ]
    assert await repository.completed_media_ids({request.media_id}) == {
        request.media_id
    }
    assert result["diagnostics"]["pipeline_completed"] is True


@pytest.mark.asyncio
async def test_checkpoint_failure_stops_before_more_work_and_releases_resources():
    analysis = Analysis.new(Document.from_payload("texto"))
    checkpoint = AsyncMock(side_effect=ConnectionError("banco indisponível"))
    next_step, resource = AsyncMock(), AsyncMock()
    next_step.name, next_step.required = "next", True

    with pytest.raises(ConnectionError):
        await AnalysisPipeline([SummaryStep(), next_step], [resource]).run(
            analysis, checkpoint
        )

    next_step.process.assert_not_awaited()
    resource.release.assert_awaited_once()
    assert analysis.pipeline_completed is False


def test_completion_marker_roundtrip_and_legacy_default():
    analysis = Analysis.new(Document.from_payload("texto"))
    analysis.pipeline_completed = True
    restored = Analysis.new(Document.from_payload("texto"))
    restore_from_diagnostics(restored, analysis_diagnostics(analysis))
    assert restored.pipeline_completed is True
    restore_from_diagnostics(restored, {})
    assert restored.pipeline_completed is False


def test_embeddings_retry_temporary_loading_failure_and_then_reuse_the_model(
    monkeypatch,
):
    import sys
    from src.text_analysis.infrastructure.adapters.embeddings_sentence_transformers_adapter import (
        SentenceTransformerEmbeddingAdapter,
    )

    model = SimpleNamespace(encode=lambda *args, **kwargs: [[0.1, 0.2]])
    attempts = []

    def load(*args, **kwargs):
        attempts.append(1)
        if len(attempts) == 1:
            raise ConnectionError("download indisponível")
        return model

    monkeypatch.setitem(
        sys.modules, "sentence_transformers", SimpleNamespace(SentenceTransformer=load)
    )
    adapter = SentenceTransformerEmbeddingAdapter("e5", device="cpu")
    with pytest.raises(TemporarilyUnavailableError):
        adapter.embed(["texto"])
    assert adapter.embed(["texto"]) == [[0.1, 0.2]]
    assert adapter.embed(["texto"]) == [[0.1, 0.2]]
    assert len(attempts) == 2


def test_concurrent_search_requests_load_one_embedding_model(monkeypatch):
    import sys
    import time
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from src.text_analysis.infrastructure.adapters.embeddings_sentence_transformers_adapter import (
        SentenceTransformerEmbeddingAdapter,
    )

    attempts = []
    model = object()
    start = Barrier(4)

    def load(*args, **kwargs):
        attempts.append(1)
        time.sleep(0.02)
        return model

    monkeypatch.setitem(
        sys.modules, "sentence_transformers", SimpleNamespace(SentenceTransformer=load)
    )
    adapter = SentenceTransformerEmbeddingAdapter("e5", device="cpu")

    def request():
        start.wait(timeout=5)
        return adapter.get_model_instance()

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda unused: request(), range(4)))

    assert all(result is model for result in results)
    assert len(attempts) == 1
