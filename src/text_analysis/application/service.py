"""Application-level service for Text Analysis.
Consolidates command and query logic into a single Service class."""

from __future__ import annotations

import logging
import time
from statistics import mean
from typing import Any, Dict, List, Optional
from uuid import UUID

from src.providers.domain.interfaces import IProviderRegistry
from src.shared.domain.events import (
    SentimentAnalysisCompleted,
    SummarizationCompleted,
    TopicModelingCompleted,
)
from .config import AnalysisConfig
from ..domain import Analysis, Document, SentimentLabel
from ..domain.errors import DomainError
from ..domain.value_objects import Sentiment, Topic
from .dto import AnalysisResultDTO
from .mappers import analysis_to_dto
from .ports import (
    AnalysisRepositoryPort,
    ChunkingServicePort,
    EmbeddingServicePort,
    SentimentServicePort,
    TextGenerationPort,
    TopicModelingPort,
)
from .metrics import TextAnalysisMetrics, NoOpTextAnalysisMetrics
from .commands.dto import AnalyzeTextCommand
from .queries.dto import GetAnalysisQuery, GetAnalysisByMediaIdQuery
from .text_analysis_read_service import TextAnalysisReadService

logger = logging.getLogger(__name__)


class TextAnalysisService:
    """Service for text analysis operations."""

    def __init__(
        self,
        *,
        sentiment_service: SentimentServicePort,
        embedding_service: EmbeddingServicePort,
        topic_modeling: TopicModelingPort,
        text_generation: TextGenerationPort,
        chunker: ChunkingServicePort,
        repository: AnalysisRepositoryPort,
        provider_registry: IProviderRegistry | None = None,
        config: Optional[AnalysisConfig] = None,
        metrics: TextAnalysisMetrics | None = None,
        event_bus: Any | None = None,
        transcription_queries: Any | None = None,
        text_analysis_read_service: TextAnalysisReadService,
    ) -> None:
        self.sentiment_service = sentiment_service
        self.embedding_service = embedding_service
        self.topic_modeling = topic_modeling
        self.text_generation = text_generation
        self.chunker = chunker
        self.repository = repository
        self.provider_registry = provider_registry
        self.config = config or AnalysisConfig()
        self.metrics = metrics or NoOpTextAnalysisMetrics()
        self.event_bus = event_bus
        self.transcription_queries = transcription_queries
        self.text_analysis_read_service = text_analysis_read_service

    def _validate_provider(self, provider: Optional[str]) -> Optional[str]:
        if provider and self.provider_registry:
            actives = {p.name for p in self.provider_registry.get_active_providers()}
            if provider not in actives:
                raise ValueError(f"Provider '{provider}' não registrado/ativo")
        return provider

    async def analyze_text_content(
        self,
        command: AnalyzeTextCommand,
    ) -> Dict[str, Any]:
        """Main orchestrator for analyzing text."""
        resolved_provider = self._validate_provider(command.language) # Provider might be inferred from language or explicitly set
        
        text_content = command.text_content
        transcription_id = command.transcription_id
        language = command.language
        segments = None # Commands do not define segments. This was coming from transcription.
        user_id = command.user_id
        media_id = command.media_id

        # Fallback: Fetch text from database if not provided but media_id is available
        if not text_content and media_id and self.transcription_queries:
            try:
                # Assuming GetMediaQuery(media_id=media_id) would work for transcription
                # Needs to be fixed based on actual transcription_queries
                transcription = await self.transcription_queries.get_by_media_id(media_id) 
                if transcription:
                    text_content = getattr(transcription, "text", "") or getattr(transcription, "content", "")
                    # Enrich missing metadata
                    if not transcription_id:
                        transcription_id = transcription.id
                    if not language:
                        language = transcription.language
                    # if not segments: # Segments might be in transcription, but command doesn't provide.
                    #     segments = transcription.segments
            except Exception as exc:
                logger.warning("text_analysis.fetch_text_failed", media_id=media_id, error=str(exc))

        start = time.perf_counter()
        success = False
        try:
            # Core Analysis Logic (Logic from AnalyzeTextCommandHandler)
            result_dto = await self._perform_analysis(
                text=text_content or "",
                segments=segments,
                language=language,
                chunk_size=None, # Options are not part of current command
                chunk_overlap=None, # Options are not part of current command
                media_id=media_id,
                transcription_id=transcription_id,
                user_id=user_id
            )
            
            result = result_dto.to_dict()
            # Enrich with ownership/context
            if media_id:
                result["media_id"] = str(media_id)
            if transcription_id:
                result["transcription_id"] = str(transcription_id)
            if resolved_provider:
                result["provider"] = resolved_provider
            if user_id:
                result["user_id"] = str(user_id)
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
                    provider=resolved_provider, # command doesn't have provider, infer from language or config
                )
            except Exception:
                pass

    async def _perform_analysis(
        self,
        text: str,
        segments: Optional[list[dict]],
        language: Optional[str],
        chunk_size: Optional[int],
        chunk_overlap: Optional[int],
        media_id: Optional[UUID],
        transcription_id: Optional[UUID],
        user_id: Optional[UUID],
    ) -> AnalysisResultDTO:
        language = language or self.config.language
        chunk_size = chunk_size or self.config.chunk_size
        chunk_overlap = chunk_overlap or self.config.chunk_overlap

        document = Document.from_payload(text, segments)
        analysis = Analysis.new(document, media_id=media_id, transcription_id=transcription_id, user_id=user_id)

        chunks = self.chunker.chunk(document, size=chunk_size, overlap=chunk_overlap)
        analysis.chunks = chunks
        logger.info("Chunked document into %d parts", len(chunks))

        sentiments = self.sentiment_service.analyze(chunks, language)
        analysis.sentiments = sentiments
        analysis.overall_sentiment = self._aggregate_sentiment(sentiments)

        embeddings = self.embedding_service.embed([chunk.text for chunk in chunks])
        topics, diagnostics = self.topic_modeling.model_topics(
            chunks, embeddings, language
        )

        topics_with_summaries = await self._summarize_topics(topics, language) # Await added
        analysis.topics = topics_with_summaries
        analysis.diagnostics = diagnostics

        analysis_id = self.repository.save(analysis)
        logger.info("Stored analysis %s", analysis_id)

        if self.event_bus is not None:
            try:
                self._emit_completed_event(analysis)
            except Exception as exc:
                logger.warning("text_analysis.event_emit_failed", error=str(exc))
        
        return analysis_to_dto(analysis)

    def _emit_completed_event(self, analysis: Analysis) -> None:
        # Sentiment summary
        overall_score = 0.0
        if analysis.sentiments:
            overall_score = sum(s.score for s in analysis.sentiments) / len(analysis.sentiments)
        
        sentiment_event = SentimentAnalysisCompleted(
            analysis_id=analysis.id,
            transcription_id=analysis.transcription_id,
            media_id=analysis.media_id,
            sentiment_score=overall_score,
            overall_sentiment=(analysis.overall_sentiment.value if analysis.overall_sentiment else None),
            provider="text_analysis",
            status="success",
            correlation_id=getattr(analysis, "correlation_id", None),
        )
        self.event_bus.publish(sentiment_event)

        # Summarization
        summarization_event = SummarizationCompleted(
            analysis_id=analysis.id,
            transcription_id=analysis.transcription_id,
            media_id=analysis.media_id,
            provider="text_analysis",
            status="success",
            correlation_id=getattr(analysis, "correlation_id", None),
        )
        self.event_bus.publish(summarization_event)

        # Topic modeling
        topic_event = TopicModelingCompleted(
            analysis_id=analysis.id,
            transcription_id=analysis.transcription_id,
            media_id=analysis.media_id,
            provider="text_analysis",
            status="success",
            correlation_id=getattr(analysis, "correlation_id", None),
        )
        self.event_bus.publish(topic_event)

    def _aggregate_sentiment(self, sentiments: List[Sentiment]) -> SentimentLabel:
        if not sentiments:
            return SentimentLabel.NEUTRAL
        positives = [s.score for s in sentiments if s.label == SentimentLabel.POSITIVE]
        negatives = [s.score for s in sentiments if s.label == SentimentLabel.NEGATIVE]
        neutrals = [s.score for s in sentiments if s.label == SentimentLabel.NEUTRAL]
        pos = mean(positives) if positives else 0.0
        neg = mean(negatives) if negatives else 0.0
        neu = mean(neutrals) if neutrals else 0.0
        scores = {
            SentimentLabel.POSITIVE: pos if pos else 0.0,
            SentimentLabel.NEUTRAL: neu if neu else 0.0,
            SentimentLabel.NEGATIVE: neg if neg else 0.0,
        }
        return max(scores, key=scores.get)

    async def _summarize_topics(self, topics: List[Topic], language: str) -> List[Topic]: # Made async
        enhanced: List[Topic] = []
        for topic in topics:
            summary_md = None
            try:
                if self.text_generation.is_available():
                    summary_md = await self.text_generation.summarize_topic( # Await added
                        topic.title,
                        "\n".join(topic.snippets),
                        topic.keywords,
                        language,
                    )
            except Exception as exc:
                logger.warning("LLM summary failed: %s", exc)
            if not summary_md:
                summary_md = self._fallback_summary(topic)
            enhanced.append(
                Topic(
                    topic_id=topic.topic_id,
                    keywords=topic.keywords,
                    snippets=topic.snippets,
                    title=topic.title or "Tópico",
                    summary_md=summary_md,
                    size=topic.size,
                    diagnostics=topic.diagnostics,
                )
            )
        return enhanced

    @staticmethod
    def _fallback_summary(topic: Topic) -> str:
        bullets = "\n".join(f"- {kw}" for kw in topic.keywords[:6])
        snippets = topic.snippets[:2]
        snippets_md = "\n".join(f"- {s}" for s in snippets)
        return (
            f"# {topic.title or 'Tópico'}\n"
            "**Resumo**\n" + bullets + "\n"
            "**Subtópicos**\n1. **Não informado**\n   - Não informado\n"
            "**Termos-chave**\n" + bullets + "\n"
            "**Trechos representativos**\n" + snippets_md
        )

    async def get_analysis(self, query: GetAnalysisQuery) -> Dict[str, Any]:
        """Retrieve analysis by ID."""
        return self.text_analysis_read_service.get_analysis(query)

    async def get_analysis_by_media_id(self, query: GetAnalysisByMediaIdQuery) -> Optional[Dict[str, Any]]:
        """Retrieve analysis by Media ID."""
        return self.text_analysis_read_service.get_analysis_by_media_id(query)

    async def list_topics(self, query: ListTopicsQuery) -> List[Topic]:
        """List topics for a given analysis."""
        return self.text_analysis_read_service.list_topics(query)
