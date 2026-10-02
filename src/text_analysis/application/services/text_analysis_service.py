"""Application-level service for Text Analysis.

Consolidates command and query logic into a single Service class.
Now uses a Pipeline pattern for granular and resilient processing.
"""

from __future__ import annotations

import inspect
import time
from typing import Any, Optional, List, Dict
from uuid import UUID

import structlog

from src.shared.application.event_bus import SupportsEventBus
from src.shared.application.ports import ProcessingStatsPort
from src.text_analysis.application.ports.repository import FeedbackRepositoryPort

from src.text_analysis.domain import Analysis, Document
from src.text_analysis.domain import Topic
from src.text_analysis.application.config import AnalysisConfig
from src.text_analysis.application.dtos import (
    AnalyzeTextCommand,
    GetAnalysisByMediaIdQuery,
    GetAnalysisQuery,
    ListTopicsQuery,
)
from src.text_analysis.application.mappers import analysis_to_dto
from src.text_analysis.application.metrics import NoOpTextAnalysisMetrics, TextAnalysisMetrics
from src.text_analysis.application.ports import (
    AnalysisRepositoryPort,
)
from src.text_analysis.application.ports.transcription_port import TranscriptionQueryPort
from src.text_analysis.application.pipeline.base import AnalysisPipeline
from src.text_analysis.application.services.text_analysis_read_service import TextAnalysisReadService

logger = structlog.get_logger(__name__)


class TextAnalysisService:
    """Service for text analysis operations."""

    def __init__(
        self,
        *,
        repository: AnalysisRepositoryPort,
        pipeline: AnalysisPipeline,
        feedback_repo: Optional[FeedbackRepositoryPort] = None,
        config: Optional[AnalysisConfig] = None,
        metrics: TextAnalysisMetrics | None = None,
        event_bus: SupportsEventBus | None = None,
        transcription_queries: Optional[TranscriptionQueryPort] = None,
        text_analysis_read_service: TextAnalysisReadService,
        stats_recorder: ProcessingStatsPort | None = None,
        runtime_diagnostics: Optional[dict] = None,
    ) -> None:
        self.repository = repository
        self.pipeline = pipeline
        self.feedback_repo = feedback_repo
        self.config = config or AnalysisConfig()
        self.metrics = metrics or NoOpTextAnalysisMetrics()
        self.event_bus = event_bus
        self.transcription_queries = transcription_queries
        self.text_analysis_read_service = text_analysis_read_service
        self.stats_recorder = stats_recorder
        # Ex.: {"hardware_target": "cuda", "compute_type": "float16"}.
        self.runtime_diagnostics = dict(runtime_diagnostics or {})

    async def submit_feedback(self, analysis_id: str, user_id: UUID, score: int, comment: str | None = None) -> bool:
        """Saves user feedback for an analysis."""
        await self.feedback_repo.save_feedback(analysis_id, user_id, score, comment)
        logger.info("text_analysis.feedback_submitted", analysis_id=analysis_id, score=score)
        return True

    async def correct_summary(self, analysis_id: str, new_summary: str) -> bool:
        """Allows manual correction of the AI summary."""
        success = await self.repository.update_summary(analysis_id, new_summary)
        if success:
            logger.info("text_analysis.summary_corrected_by_human", analysis_id=analysis_id)
        return success


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
                await self.repository.save(current)

            pipeline_started = time.perf_counter()
            analysis = await self.pipeline.run(analysis, on_step_completed=checkpoint)
            await self._record_durations(analysis, time.perf_counter() - pipeline_started)

            analysis_id = await self.repository.save(analysis)
            logger.info("text_analysis.stored", analysis_id=analysis_id)

            if self.event_bus:
                await self._emit_completed_events(analysis)

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
            if text_source:
                text_content = text_content or text_source.text
                transcription_id = transcription_id or text_source.id
                segments = list(text_source.segments or [])
                language = getattr(text_source, "language", None)
                visual_context = list(getattr(text_source, "visual_context", None) or [])
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
                analysis.id = existing.id
        analysis.diagnostics.update(media_info)
        # Idioma detectado na transcrição: palavras vazias e sentimento
        # seguem o idioma da gravação (o resumo continua em português).
        if language and language.lower() not in ("auto", "unknown"):
            analysis.diagnostics["language"] = language.lower()
        # O que aparecia na tela, descrito no processamento do vídeo.
        if visual_context:
            analysis.diagnostics["visual_context"] = visual_context
        # Dispositivo e precisão em uso, informados pela montagem do módulo.
        analysis.diagnostics.update(self.runtime_diagnostics)
        return analysis

    async def _record_metrics(self, media_id, user_id, duration: float, success: bool) -> None:
        try:
            if hasattr(self.metrics, "set_context"):
                self.metrics.set_context(str(media_id), str(user_id))
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
        statuses = analysis.diagnostics.get("steps", {})
        try:
            await self.stats_recorder.log_stat(
                "text_analysis", total_seconds, text_size, media_seconds, self.config.llm_model
            )
            for step, seconds in analysis.diagnostics.get("step_seconds", {}).items():
                ok = statuses.get(step) == "ok"
                await self.stats_recorder.log_stat(
                    f"analysis.{step}", seconds, text_size, media_seconds, None,
                    "success" if ok else "failed",
                )
        except Exception as exc:  # estatística nunca pode derrubar a análise
            logger.warning("text_analysis.stats_record_failed", error=str(exc))

    async def _emit_completed_events(self, analysis: Analysis) -> None:
        """Publishes domain events for successful stages of the pipeline."""
        if not self.event_bus: return
        
        # Helper to avoid repetitive boilerplate
        async def _pub(event):
            try:
                res = self.event_bus.publish(event)
                if inspect.isawaitable(res): await res
            except Exception as e:
                logger.warning("text_analysis.event_emit_failed", error=str(e))

        if analysis.overall_sentiment:
            from src.shared.domain.events import SentimentAnalysisCompleted
            await _pub(SentimentAnalysisCompleted(
                analysis_id=str(analysis.id),
                media_id=str(analysis.media_id) if analysis.media_id else None,
                overall_sentiment=analysis.overall_sentiment.value,
                correlation_id=analysis.correlation_id
            ))

        if analysis.summary:
            from src.shared.domain.events import SummarizationCompleted
            await _pub(SummarizationCompleted(
                analysis_id=str(analysis.id),
                media_id=str(analysis.media_id) if analysis.media_id else None,
                summary=analysis.summary,
                correlation_id=analysis.correlation_id
            ))

        if analysis.topics:
            from src.shared.domain.events import TopicModelingCompleted
            await _pub(TopicModelingCompleted(
                analysis_id=str(analysis.id),
                media_id=str(analysis.media_id) if analysis.media_id else None,
                topics=analysis.topics,
                correlation_id=analysis.correlation_id
            ))

    async def get_analysis(self, query: GetAnalysisQuery) -> Dict[str, Any]:
        return await self.text_analysis_read_service.get_analysis(query)

    async def get_analysis_by_media_id(self, query: GetAnalysisByMediaIdQuery) -> Optional[Dict[str, Any]]:
        return await self.text_analysis_read_service.get_analysis_by_media_id(query)

    async def list_topics(self, query: ListTopicsQuery) -> List[Topic]:
        return await self.text_analysis_read_service.list_topics(query)

