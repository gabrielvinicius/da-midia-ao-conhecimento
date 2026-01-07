"""Application-level service for Text Analysis.

Consolidates command and query logic into a single Service class.
Now uses a Pipeline pattern for granular and resilient processing.
"""

from __future__ import annotations

import inspect
import time
from statistics import mean
from typing import Any, Optional, List, Dict
from uuid import UUID

from src.shared.domain.events import (
    SentimentAnalysisCompleted,
    SummarizationCompleted,
    TopicModelingCompleted,
)
from src.shared.infrastructure.observability.logging.logging_config import get_logger
from src.text_analysis.config.settings import text_analysis_settings

from src.text_analysis.domain import Analysis, Document, SentimentLabel
from src.text_analysis.domain import Sentiment, Topic
from src.text_analysis.application.config import AnalysisConfig
from src.text_analysis.application.dtos import (
    AnalysisResultDTO,
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
from src.text_analysis.application.pipeline.steps import (
    ChunkingStep,
    SentimentStep,
    TopicModelingStep,
    SummarizationStep,
)
from src.text_analysis.application.services.text_analysis_read_service import TextAnalysisReadService

logger = get_logger(__name__)


class TextAnalysisService:
    """Service for text analysis operations."""

    def __init__(
        self,
        *,
        repository: AnalysisRepositoryPort,
        pipeline: AnalysisPipeline, # NEW: Explicit Pipeline injection
        config: Optional[AnalysisConfig] = None,
        metrics: TextAnalysisMetrics | None = None,
        event_bus: Any | None = None,
        transcription_queries: Optional[TranscriptionQueryPort] = None,
        text_analysis_read_service: TextAnalysisReadService,
        settings=text_analysis_settings,
    ) -> None:
        self.repository = repository
        self.pipeline = pipeline
        self.config = config or AnalysisConfig()
        self.metrics = metrics or NoOpTextAnalysisMetrics()
        self.event_bus = event_bus
        self.transcription_queries = transcription_queries
        self.text_analysis_read_service = text_analysis_read_service
        self.settings = settings

    async def analyze_text_content(
        self,
        command: AnalyzeTextCommand,
    ) -> dict[str, Any]:
        """Main orchestrator for analyzing text content."""
        text_content = command.text_content
        transcription_id = command.transcription_id
        language = command.language or self.config.language
        user_id = command.user_id
        media_id = command.media_id

        # 1. Fetch text source via Port if not provided
        if not text_content and media_id and self.transcription_queries:
            try:
                # Explicit call to the port returning strict DTO
                text_source = await self.transcription_queries.get_text_source(media_id)
                if text_source:
                    text_content = text_source.text
                    transcription_id = transcription_id or text_source.id
                    language = language or text_source.language
            except Exception as exc:
                logger.warning("text_analysis.fetch_text_failed", media_id=str(media_id), error=str(exc))

        start = time.perf_counter()
        success = False
        try:
            # 2. Level 6.0: Predictive Observability
            from src.shared.infrastructure.monitoring.resource_predictor import ResourcePredictor, RiskLevel
            predictor = ResourcePredictor()
            prediction = predictor.predict_analysis_cost(len(text_content or ""))
            
            logger.info("text_analysis.predictive_cost", 
                        estimated_duration=f"{prediction.estimated_duration_seconds}s",
                        vram_needed=f"{prediction.vram_required_gb}GB",
                        risk=prediction.risk_level.value)

            if prediction.risk_level == RiskLevel.DANGEROUS:
                logger.warning("text_analysis.proactive_mitigation_active", reason=prediction.recommendation)
                # Proactively reduce chunk size to mitigate predicted OOM
                self.pipeline.steps[0].size = (self.config.chunk_size or 500) // 2

            # 3. Create Analysis Aggregate
            document = Document.from_payload(text_content or "", None)
            analysis = Analysis.new(
                document,
                media_id=media_id,
                transcription_id=transcription_id,
                user_id=user_id,
            )

            # 4. Run Granular Pipeline
            try:
                # Inject initial hardware context into diagnostics
                analysis.diagnostics["engine"] = "Adaptive Pipeline v6.0"
                from src.shared.infrastructure.config.settings import settings
                analysis.diagnostics["hardware_target"] = settings.resolved_device
                analysis.diagnostics["compute_type"] = settings.ai_compute_type
                
                analysis = await self.pipeline.run(analysis)
            except Exception as exc:
                logger.warning("text_analysis.pipeline_failed_attempting_self_healing", error=str(exc))
                # Level 6.0 Self-Healing: Adaptive Recovery
                # Reset analysis state partially to avoid mixed results from failed run
                analysis.chunks = []
                analysis.sentiments = []
                analysis.topics = []
                
                # Reduce intensity: Half chunk size, double caution
                new_chunk_size = (self.config.chunk_size or 500) // 2
                self.pipeline.steps[0].size = new_chunk_size
                logger.info("text_analysis.self_healing_retry", new_chunk_size=new_chunk_size)
                
                analysis = await self.pipeline.run(analysis)

            # 5. Final Persistence
            analysis_id = await self.repository.save(analysis)
            logger.info("text_analysis.stored", analysis_id=analysis_id)

            # 6. Emit Events
            if self.event_bus:
                await self._emit_completed_events(analysis)

            result_dto = analysis_to_dto(analysis)
            result = result_dto.to_dict()
            
            # Enrich result with IDs for API response
            if media_id: result["media_id"] = str(media_id)
            if transcription_id: result["transcription_id"] = str(transcription_id)
            if user_id: result["user_id"] = str(user_id)
            
            success = True
            return result
        finally:
            try:
                if hasattr(self.metrics, "set_context"):
                    self.metrics.set_context(str(media_id), str(user_id))
                await self.metrics.record_operation(
                    operation="analyze_text_content",
                    duration=time.perf_counter() - start,
                    success=success,
                )
            except Exception: pass

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
                correlation_id=getattr(analysis, "correlation_id", None)
            ))

        if analysis.summary:
            from src.shared.domain.events import SummarizationCompleted
            await _pub(SummarizationCompleted(
                analysis_id=str(analysis.id),
                media_id=str(analysis.media_id) if analysis.media_id else None,
                summary=analysis.summary,
                correlation_id=getattr(analysis, "correlation_id", None)
            ))

        if analysis.topics:
            from src.shared.domain.events import TopicModelingCompleted
            await _pub(TopicModelingCompleted(
                analysis_id=str(analysis.id),
                media_id=str(analysis.media_id) if analysis.media_id else None,
                topics=analysis.topics,
                correlation_id=getattr(analysis, "correlation_id", None)
            ))

    async def get_analysis(self, query: GetAnalysisQuery) -> Dict[str, Any]:
        return await self.text_analysis_read_service.get_analysis(query)

    async def get_analysis_by_media_id(self, query: GetAnalysisByMediaIdQuery) -> Optional[Dict[str, Any]]:
        return await self.text_analysis_read_service.get_analysis_by_media_id(query)

    async def list_topics(self, query: ListTopicsQuery) -> List[Topic]:
        return await self.text_analysis_read_service.list_topics(query)

    async def estimate_cost(self, media_id: UUID) -> Dict[str, Any]:
        """Prediz o custo e tempo de processamento antes da execução."""
        if not self.transcription_queries:
            return {"status": "unknown", "reason": "No text source available"}
            
        source = await self.transcription_queries.get_text_source(media_id)
        if not source:
            return {"status": "unknown", "reason": "Transcription not found"}
            
        from src.shared.infrastructure.monitoring.resource_predictor import ResourcePredictor
        predictor = ResourcePredictor()
        prediction = predictor.predict_analysis_cost(len(source.text))
        
        return {
            "estimated_seconds": prediction.estimated_duration_seconds,
            "vram_gb": prediction.vram_required_gb,
            "risk": prediction.risk_level.value,
            "recommendation": prediction.recommendation
        }