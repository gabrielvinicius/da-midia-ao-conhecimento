"""Registro e resumo das durações de processamento."""

from types import SimpleNamespace

import pytest

from src.shared.infrastructure.repositories.processing_stats_repository import summarize_rows
from src.text_analysis.application.pipeline.base import AnalysisPipeline, AnalysisStep
from src.text_analysis.application.services.text_analysis_service import TextAnalysisService
from src.text_analysis.domain import Analysis, Document


def _row(task, seconds, media=None, model=None, status="success"):
    return SimpleNamespace(
        task_type=task, processing_duration_seconds=seconds, input_duration_seconds=media,
        model_name=model, status=status,
    )


def test_summary_groups_by_task_and_model():
    # 3 transcrições de 60 s de áudio: 10, 20 e 30 s de processamento; 1 falha
    rows = [_row("transcription", s, 60.0, "FasterWhisper") for s in (10.0, 20.0, 30.0)]
    rows += [_row("transcription", 5.0, 60.0, "FasterWhisper", status="failed"), _row("analysis.synthesis", 42.0)]

    summary = {(i["task_type"], i["model_name"]): i for i in summarize_rows(rows)}

    t = summary[("transcription", "FasterWhisper")]
    assert (t["runs"], t["failures"]) == (4, 1)
    assert (t["avg_seconds"], t["median_seconds"], t["max_seconds"]) == (20.0, 20.0, 30.0)
    assert t["realtime_factor"] == round(60 / 180, 3)  # 60 s de processamento / 180 s de áudio
    assert summary[("analysis.synthesis", None)]["realtime_factor"] is None


class _Step(AnalysisStep):
    def __init__(self, name, fail=False):
        self._name, self._fail = name, fail

    @property
    def name(self):
        return self._name

    async def process(self, analysis):
        if self._fail:
            raise RuntimeError("falhou")
        return analysis


class _Recorder:
    def __init__(self):
        self.rows = []

    async def log_stat(self, task_type, seconds, size=None, media_seconds=None, model=None, status="success"):
        self.rows.append((task_type, media_seconds, status))


@pytest.mark.asyncio
async def test_pipeline_times_steps_and_service_records_them():
    recorder = _Recorder()
    pipeline = AnalysisPipeline(steps=[_Step("chunking"), _Step("synthesis", fail=True)])

    class _Repo:
        async def save(self, analysis):
            return str(analysis.id)

    service = TextAnalysisService(
        repository=_Repo(), pipeline=pipeline, text_analysis_read_service=None,
        stats_recorder=recorder,
    )
    analysis = Analysis.new(Document.from_payload("oi", [{"text": "oi", "start": 0, "end": 90.0}]))
    analysis = await pipeline.run(analysis)
    await service._record_durations(analysis, 1.5)

    assert set(analysis.diagnostics["step_seconds"]) == {"chunking", "synthesis"}
    assert recorder.rows == [
        ("text_analysis", 90.0, "success"),
        ("analysis.chunking", 90.0, "success"),
        ("analysis.synthesis", 90.0, "failed"),
    ]
