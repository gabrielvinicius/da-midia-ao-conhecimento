"""Execução da análise de uma mídia (no worker), pelo pipeline de etapas.

Leitura, revisão humana e pedidos de análise feitos pela API ficam em
serviços próprios (TextAnalysisReadService, AnalysisReviewService,
AnalysisRequestService): a API não monta o pipeline nem carrega modelos.
"""

from __future__ import annotations

import time
from typing import Any, Optional

import structlog

from src.shared.application.event_bus import SupportsEventBus
from src.shared.application.ports import ProcessingStatsPort
from src.shared.domain.events import AnalysisCompleted
from src.shared.domain.errors import ConflictError, NotFoundError

from src.text_analysis.domain import Analysis, Document
from src.text_analysis.domain.entities.analysis import AnalysisSourceChangedError
from src.text_analysis.application.config import AnalysisConfig
from src.text_analysis.application.dtos import (
    AnalyzeTextCommand,
)
from src.text_analysis.application.mappers import analysis_to_dto
from src.text_analysis.application.metrics import NoOpTextAnalysisMetrics, TextAnalysisMetrics
from src.text_analysis.application.ports import (
    AnalysisRepositoryPort,
)
from src.text_analysis.application.ports.transcription_port import TranscriptionQueryPort
from src.text_analysis.application.pipeline.base import AnalysisPipeline

logger = structlog.get_logger(__name__)


class TextAnalysisService:
    """Service for text analysis operations."""

    def __init__(
        self,
        *,
        repository: AnalysisRepositoryPort,
        pipeline: AnalysisPipeline,
        config: Optional[AnalysisConfig] = None,
        metrics: TextAnalysisMetrics | None = None,
        event_bus: SupportsEventBus | None = None,
        transcription_queries: Optional[TranscriptionQueryPort] = None,
        stats_recorder: ProcessingStatsPort | None = None,
        runtime_diagnostics: Optional[dict] = None,
    ) -> None:
        self.repository = repository
        self.pipeline = pipeline
        self.config = config or AnalysisConfig()
        self.metrics = metrics or NoOpTextAnalysisMetrics()
        self.event_bus = event_bus
        self.transcription_queries = transcription_queries
        self.stats_recorder = stats_recorder
        # Ex.: {"hardware_target": "cuda", "compute_type": "float16"}.
        self.runtime_diagnostics = dict(runtime_diagnostics or {})

    async def analyze_text_content(
        self,
        command: AnalyzeTextCommand,
    ) -> dict[str, Any]:
        """Main orchestrator for analyzing text content."""
        media_id, user_id = command.media_id, command.user_id
        start = time.perf_counter()
        success = False
        try:
            analysis = await self._new_analysis(command)

            # Pipeline granular. Cada etapa grava seu resultado ao terminar
            # (checkpoint); se o worker cair no meio, o que já foi calculado
            # continua disponível.
            async def checkpoint(current: Analysis, step_name: str) -> None:
                await self.repository.save_generated(current)

            pipeline_started = time.perf_counter()
            analysis = await self.pipeline.run(analysis, on_step_completed=checkpoint)
            await self._record_durations(analysis, time.perf_counter() - pipeline_started)

            analysis.pipeline_completed = True
            analysis_id = await self.repository.save_generated(analysis)
            logger.info("text_analysis.stored", analysis_id=analysis_id)

            if self.event_bus:
                await self._announce_completed(analysis)

            result = analysis_to_dto(analysis).to_dict()
            # Identificadores para a resposta da API.
            for key, value in (
                ("media_id", media_id),
                ("transcription_id", analysis.transcription_id),
                ("user_id", user_id),
            ):
                if value:
                    result[key] = str(value)

            success = True
            return result
        finally:
            await self._record_metrics(media_id, user_id, time.perf_counter() - start, success)

    async def _new_analysis(self, command: AnalyzeTextCommand) -> Analysis:
        """Monta o agregado da análise com o texto, os trechos e o contexto da mídia.

        Mesmo quando o texto já vem no comando, os segmentos (com horários) só
        existem na transcrição; sem eles, a análise visual e os horários da busca
        semântica não funcionam. Uma falha ao ler a transcrição interrompe a
        análise (a tarefa tenta de novo), em vez de seguir com um resultado pior
        em silêncio.
        """
        text_content = command.text_content
        transcription_id = command.transcription_id
        media_id = command.media_id
        segments: list = []
        language: Optional[str] = None
        visual_context: list = []
        media_info: dict = {}

        if media_id and self.transcription_queries:
            text_source = await self.transcription_queries.get_text_source(media_id)
            if text_source is None:
                raise NotFoundError("O texto desta mídia não está disponível para análise.")
            if transcription_id is not None and transcription_id != text_source.id:
                raise AnalysisSourceChangedError("A transcrição deste pedido de análise foi substituída.")
            if not text_source.text.strip():
                raise ConflictError("O texto desta mídia ainda não está pronto para análise.")
            text_content = text_source.text
            transcription_id = text_source.id
            segments = list(text_source.segments or [])
            language = text_source.language
            visual_context = list(text_source.visual_context or [])
            # Dados da mídia (tipo, arquivo) usados pelas etapas da análise.
            media_info = await self.transcription_queries.get_media_info(media_id) or {}

        analysis = Analysis.new(
            Document.from_payload(text_content or "", segments),
            media_id=media_id,
            transcription_id=transcription_id,
            user_id=command.user_id,
        )
        analysis.correlation_id = command.correlation_id
        # Uma análise por mídia: uma nova tentativa grava sobre a anterior
        # (e as gravações parciais dela), em vez de criar outra.
        if media_id:
            existing = await self.repository.get_by_media_id(str(media_id))
            if existing is not None:
                existing.ensure_can_regenerate()
                analysis.id = existing.id
        analysis.diagnostics.update(media_info)
        # Idioma detectado na transcrição: palavras vazias e sentimento
        # seguem o idioma da gravação (o resumo continua em português).
        analysis.set_language(language)
        # O que aparecia na tela, descrito no processamento do vídeo.
        analysis.visual_context = visual_context
        # Dispositivo e precisão em uso, informados pela montagem do módulo.
        analysis.diagnostics.update(self.runtime_diagnostics)
        return analysis

    async def _record_metrics(self, media_id, user_id, duration: float, success: bool) -> None:
        try:
            await self.metrics.record_operation(
                operation="analyze_text_content",
                duration=duration,
                success=success,
            )
        except Exception as exc:  # métrica nunca derruba a análise
            logger.warning("text_analysis.metrics_failed", error=str(exc))

    async def _record_durations(self, analysis: Analysis, total_seconds: float) -> None:
        """Grava a duração total e a de cada etapa (para avaliação e estimativas)."""
        if not self.stats_recorder:
            return
        segments = analysis.document.segments or []
        media_seconds = segments[-1].get("end") if segments and isinstance(segments[-1], dict) else None
        text_size = len((analysis.document.text or "").encode("utf-8"))
        try:
            await self.stats_recorder.log_stat(
                "text_analysis", total_seconds, text_size, media_seconds, self.config.llm_model
            )
            for step, seconds in analysis.step_seconds.items():
                await self.stats_recorder.log_stat(
                    f"analysis.{step}", seconds, text_size, media_seconds, None,
                    "success" if analysis.step_succeeded(step) else "failed",
                )
        except Exception as exc:  # estatística nunca pode derrubar a análise
            logger.warning("text_analysis.stats_record_failed", error=str(exc))

    async def _announce_completed(self, analysis: Analysis) -> None:
        """Anuncia o fim da análise. Quem quiser reagir (avisos ao usuário,
        novas camadas) assina AnalysisCompleted, sem que a análise o conheça.

        Uma falha de quem reage não desfaz a análise já gravada.
        """
        event = AnalysisCompleted(
            analysis_id=str(analysis.id),
            media_id=str(analysis.media_id) if analysis.media_id else None,
            transcription_id=str(analysis.transcription_id) if analysis.transcription_id else None,
            user_id=str(analysis.user_id) if analysis.user_id else None,
            summary_source=analysis.summary_source.value if analysis.summary_source else None,
            overall_sentiment=analysis.overall_sentiment.value if analysis.overall_sentiment else None,
            topic_titles=[t.title for t in analysis.main_topics if t.title],
            failed_steps=analysis.failed_steps,
            correlation_id=analysis.correlation_id,
        )
        try:
            await self.event_bus.publish(event)
        except Exception as exc:
            logger.warning("text_analysis.completed_event_failed", error=str(exc))
