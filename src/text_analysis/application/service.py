"""Application-level service for Text Analysis.

Consolidates command and query logic into a single Service class.
"""

from __future__ import annotations

import logging
import time
from statistics import mean
from typing import Any, Dict, List, Optional

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

    def _validate_provider(self, provider: Optional[str]) -> Optional[str]:
        if provider and self.provider_registry:
            actives = {p.name for p in self.provider_registry.get_active_providers()}
            if provider not in actives:
                raise ValueError(f"Provider '{provider}' não registrado/ativo")
        return provider

    async def analyze_text_content(
        self,
        *,
        media_id: Optional[str] = None,
        transcription_id: Optional[str] = None,
        text_content: Optional[str],
        segments: Optional[list[dict]] = None,
        language: Optional[str] = None,
        provider: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Main orchestrator for analyzing text."""
        resolved_provider = self._validate_provider(provider)
        
        # Fallback: Fetch text from database if not provided but media_id is available
        if not text_content and media_id and self.transcription_queries:
            try:
                transcription = await self.transcription_queries.get_by_media_id(media_id)
                if transcription:
                    text_content = getattr(transcription, "text", "") or getattr(transcription, "content", "")
                    # Enrich missing metadata
                    if not transcription_id:
                        transcription_id = str(transcription.id)
                    if not language:
                        language = transcription.language
                    if not segments:
                        segments = transcription.segments
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
                chunk_size=options.get("chunk_size") if options else None,
                chunk_overlap=options.get("chunk_overlap") if options else None,
                media_id=media_id,
                transcription_id=transcription_id,
                user_id=user_id
            )
            
            result = result_dto.to_dict()
            # Enrich with ownership/context
            if media_id:
                result["media_id"] = media_id
            if transcription_id:
                result["transcription_id"] = transcription_id
            if resolved_provider:
                result["provider"] = resolved_provider
            if user_id:
                result["user_id"] = user_id
            success = True
            return result
        finally:
            try:
                if hasattr(self.metrics, "set_context"):
                    self.metrics.set_context(media_id, user_id)
                await self.metrics.record_operation(
                    operation="analyze_text_content",
                    duration=time.perf_counter() - start,
                    success=success,
                    provider=provider or resolved_provider,
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
        media_id: Optional[str],
        transcription_id: Optional[str],
        user_id: Optional[str],
    ) -> AnalysisResultDTO:
        language = language or self.config.language
        chunk_size = chunk_size or self.config.chunk_size
        chunk_overlap = chunk_overlap or self.config.chunk_overlap

        document = Document.from_payload(text, segments)
        analysis = Analysis.new(document)
        analysis.media_id = media_id
        analysis.transcription_id = transcription_id
        analysis.user_id = user_id

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

        topics_with_summaries = self._summarize_topics(topics, language)
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
            transcription_id=getattr(analysis.document, "id", ""),
            media_id=getattr(analysis, "media_id", None),
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
            transcription_id=getattr(analysis.document, "id", ""),
            media_id=getattr(analysis, "media_id", None),
            provider="text_analysis",
            status="success",
            correlation_id=getattr(analysis, "correlation_id", None),
        )
        self.event_bus.publish(summarization_event)

        # Topic modeling
        topic_event = TopicModelingCompleted(
            analysis_id=analysis.id,
            transcription_id=getattr(analysis.document, "id", ""),
            media_id=getattr(analysis, "media_id", None),
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

    def _summarize_topics(self, topics: List[Topic], language: str) -> List[Topic]:
        enhanced: List[Topic] = []
        for topic in topics:
            summary_md = None
            try:
                if self.text_generation.is_available():
                    summary_md = self.text_generation.summarize_topic(
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

    async def schedule_summarization_task(self, **kwargs) -> Dict[str, Any]:
        logger.info("schedule_summarization_task", extra=kwargs)
        return await self.analyze_text_content(
            media_id=kwargs.get("media_id"),
            transcription_id=kwargs.get("transcription_id"),
            text_content=kwargs.get("text_content"),
            segments=kwargs.get("segments"),
            language=kwargs.get("language"),
            provider=kwargs.get("provider"),
            options=kwargs.get("options"),
        )

    async def schedule_sentiment_analysis_task(self, **kwargs) -> Dict[str, Any]:
        logger.info("schedule_sentiment_analysis_task", extra=kwargs)
        return await self.analyze_text_content(
            media_id=kwargs.get("media_id"),
            transcription_id=kwargs.get("transcription_id"),
            text_content=kwargs.get("text"),
            segments=kwargs.get("segments"),
            language=kwargs.get("language"),
            provider=kwargs.get("provider"),
            options=kwargs.get("options"),
        )

    async def schedule_topic_modeling_task(self, **kwargs) -> Dict[str, Any]:
        logger.info("schedule_topic_modeling_task", extra=kwargs)
        return await self.analyze_text_content(
            media_id=kwargs.get("media_id"),
            text_content=kwargs.get("text_content"),
            segments=kwargs.get("segments"),
            language=kwargs.get("language"),
            provider=kwargs.get("provider"),
            options=kwargs.get("options"),
        )

    def get_analysis(self, analysis_id: str) -> Dict[str, Any]:
        """Retrieve analysis by ID."""
        analysis = self.repository.get(analysis_id)
        if not analysis:
            raise DomainError(f"Analysis {analysis_id} not found")
        return analysis_to_dto(analysis).to_dict()

    def get_analysis_by_media_id(self, media_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve analysis by Media ID."""
        analysis = self.repository.get_by_media_id(media_id)
        if not analysis:
            return None
        return analysis_to_dto(analysis).to_dict()

    def list_topics(self, analysis_id: str) -> list:
        """List topics for a given analysis."""
        topics = self.repository.list_topics(analysis_id)
        if topics is None:
            raise DomainError(f"Analysis {analysis_id} not found")
        return [t.__dict__ for t in topics]