"""Application-level service for Text Analysis.

Consolidates command and query logic into a single Service class.
"""

from __future__ import annotations

import inspect
import logging
import time
from statistics import mean
from typing import Any, Dict, List, Optional
from uuid import UUID

from src.shared.domain.events import (
    SentimentAnalysisCompleted,
    SummarizationCompleted,
    TopicModelingCompleted,
)
from src.text_analysis.config.settings import text_analysis_settings

from ...domain import Analysis, Document, SentimentLabel
from ...domain import Sentiment, Topic
from ..config import AnalysisConfig
from ..dtos import (
    AnalysisResultDTO,
    AnalyzeTextCommand,
    GetAnalysisByMediaIdQuery,
    GetAnalysisQuery,
    ListTopicsQuery,
)
from ..mappers import analysis_to_dto
from ..metrics import NoOpTextAnalysisMetrics, TextAnalysisMetrics
from ..ports import (
    AnalysisRepositoryPort,
    ChunkingServicePort,
    EmbeddingServicePort,
    SentimentServicePort,
    TextGenerationPort,
    TopicModelingPort,
    TranscriptionQueryPort,
)
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
        config: Optional[AnalysisConfig] = None,
        metrics: TextAnalysisMetrics | None = None,
        event_bus: Any | None = None,
        transcription_queries: Optional[TranscriptionQueryPort] = None,
        text_analysis_read_service: TextAnalysisReadService,
        settings=text_analysis_settings,
    ) -> None:
        self.sentiment_service = sentiment_service
        self.embedding_service = embedding_service
        self.topic_modeling = topic_modeling
        self.text_generation = text_generation
        self.chunker = chunker
        self.repository = repository
        self.config = config or AnalysisConfig()
        self.metrics = metrics or NoOpTextAnalysisMetrics()
        self.event_bus = event_bus
        self.transcription_queries = transcription_queries
        self.text_analysis_read_service = text_analysis_read_service
        self.settings = settings

    def _validate_provider(self, provider: Optional[str]) -> Optional[str]:
        return provider

    async def analyze_text_content(
        self,
        command: AnalyzeTextCommand,
    ) -> Dict[str, Any]:
        """Main orchestrator for analyzing text."""
        resolved_provider = self._validate_provider(command.language)

        text_content = command.text_content
        transcription_id = command.transcription_id
        language = command.language
        segments = None
        user_id = command.user_id
        media_id = command.media_id

        if not text_content and media_id and self.transcription_queries:
            try:
                transcription = await self.transcription_queries.get_by_media_id(
                    media_id
                )
                if transcription:
                    text_content = getattr(transcription, "text", "") or getattr(
                        transcription, "content", ""
                    )
                    if not transcription_id:
                        transcription_id = transcription.id
                    if not language:
                        language = transcription.language
            except Exception as exc:
                logger.warning(
                    "text_analysis.fetch_text_failed",
                    media_id=media_id,
                    error=str(exc),
                )

        start = time.perf_counter()
        success = False
        try:
            result_dto = await self._perform_analysis(
                text=text_content or "",
                segments=segments,
                language=language,
                chunk_size=None,
                chunk_overlap=None,
                media_id=media_id,
                transcription_id=transcription_id,
                user_id=user_id,
            )

            result = result_dto.to_dict()
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
                    provider=resolved_provider,
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
        analysis = Analysis.new(
            document,
            media_id=media_id,
            transcription_id=transcription_id,
            user_id=user_id,
        )

        chunks = self.chunker.chunk(document, size=chunk_size, overlap=chunk_overlap)
        analysis.chunks = chunks
        logger.info("Chunked document into %d parts", len(chunks))

        sentiments_result = self.sentiment_service.analyze(chunks, language)
        sentiments = await sentiments_result if inspect.isawaitable(sentiments_result) else sentiments_result
        analysis.sentiments = sentiments
        analysis.overall_sentiment = self._aggregate_sentiment(sentiments)

        embeddings_result = self.embedding_service.embed([chunk.text for chunk in chunks])
        embeddings = await embeddings_result if inspect.isawaitable(embeddings_result) else embeddings_result

        topics_result = self.topic_modeling.model_topics(chunks, embeddings, language)
        topics, diagnostics = (
            await topics_result if inspect.isawaitable(topics_result) else topics_result
        )

        topics_with_summaries = await self._summarize_topics(topics, language)
        analysis.topics = topics_with_summaries
        analysis.diagnostics = diagnostics

        analysis_id = await self.repository.save(analysis)
        logger.info("Stored analysis %s", analysis_id)

        if self.event_bus is not None:
            try:
                await self._emit_completed_event(analysis)
            except Exception as exc:
                logger.warning("text_analysis.event_emit_failed", error=str(exc))

        return analysis_to_dto(analysis)

    async def _publish_event(self, event: Any) -> None:
        publish = getattr(self.event_bus, "publish", None)
        if publish is None:
            return

        result = publish(event)
        if inspect.isawaitable(result):
            await result

    async def _emit_completed_event(self, analysis: Analysis) -> None:
        overall_score = 0.0
        if analysis.sentiments:
            overall_score = sum(s.score for s in analysis.sentiments) / len(
                analysis.sentiments
            )

        sentiment_event = SentimentAnalysisCompleted(
            analysis_id=str(analysis.id),
            transcription_id=(
                str(analysis.transcription_id) if analysis.transcription_id else ""
            ),
            media_id=str(analysis.media_id) if analysis.media_id else None,
            user_id=str(analysis.user_id) if analysis.user_id else None,
            sentiment_score=overall_score,
            overall_sentiment=(
                analysis.overall_sentiment.value
                if analysis.overall_sentiment
                else None
            ),
            provider="text_analysis",
            status="success",
            correlation_id=getattr(analysis, "correlation_id", None),
        )
        await self._publish_event(sentiment_event)

        summarization_event = SummarizationCompleted(
            analysis_id=str(analysis.id),
            transcription_id=(
                str(analysis.transcription_id) if analysis.transcription_id else None
            ),
            media_id=str(analysis.media_id) if analysis.media_id else None,
            user_id=str(analysis.user_id) if analysis.user_id else None,
            provider="text_analysis",
            status="success",
            correlation_id=getattr(analysis, "correlation_id", None),
        )
        await self._publish_event(summarization_event)

        topic_event = TopicModelingCompleted(
            analysis_id=str(analysis.id),
            transcription_id=(
                str(analysis.transcription_id) if analysis.transcription_id else None
            ),
            media_id=str(analysis.media_id) if analysis.media_id else None,
            user_id=str(analysis.user_id) if analysis.user_id else None,
            provider="text_analysis",
            status="success",
            correlation_id=getattr(analysis, "correlation_id", None),
        )
        await self._publish_event(topic_event)

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

    async def _summarize_topics(
        self, topics: List[Topic], language: str
    ) -> List[Topic]:
        enhanced: List[Topic] = []
        for topic in topics:
            summary_md = None
            try:
                if self.text_generation.is_available():
                    summary_md = await self.text_generation.summarize_topic(
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
                    id=getattr(topic, "topic_id", getattr(topic, "id", 0)),
                    keywords=topic.keywords,
                    snippets=getattr(topic, "snippets", []),
                    title=getattr(topic, "title", None) or "Tópico",
                    summary=summary_md,
                    diagnostics=getattr(topic, "diagnostics", {}),
                )
            )
        return enhanced

    @staticmethod
    def _fallback_summary(topic: Topic) -> str:
        bullets = "\n".join(f"- {kw}" for kw in topic.keywords[:6])
        snippets = getattr(topic, "snippets", [])[:2]
        snippets_md = "\n".join(f"- {s}" for s in snippets)
        title = getattr(topic, "title", None)
        base = [f"# {title or 'Tópico'}", "**Termos-chave**", bullets]
        if snippets_md:
            base += ["**Trechos representativos**", snippets_md]
        return "\n".join(base)

    async def get_analysis(self, query: GetAnalysisQuery) -> Dict[str, Any]:
        """Retrieve analysis by ID."""
        return await self.text_analysis_read_service.get_analysis(query)

    async def get_analysis_by_media_id(
        self, query: GetAnalysisByMediaIdQuery
    ) -> Optional[Dict[str, Any]]:
        """Retrieve analysis by Media ID."""
        return await self.text_analysis_read_service.get_analysis_by_media_id(query)

    async def list_topics(self, query: ListTopicsQuery) -> List[Topic]:
        """List topics for a given analysis."""
        return await self.text_analysis_read_service.list_topics(query)
