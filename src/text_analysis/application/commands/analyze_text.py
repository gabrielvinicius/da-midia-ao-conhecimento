"""AnalyzeText command and handler implementing CQRS command side."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from statistics import mean
from typing import List, Optional

from ...domain import Analysis, Document, SentimentLabel
from ...domain.value_objects import Sentiment, TextChunk, Topic
from ..config import AnalysisConfig
from ..dto import AnalysisResultDTO
from ..mappers import analysis_to_dto
from ..ports import (
    AnalysisRepositoryPort,
    ChunkingServicePort,
    EmbeddingServicePort,
    SentimentServicePort,
    TextGenerationPort,
    TopicModelingPort,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AnalyzeTextCommand:
    text: str
    segments: Optional[list[dict]] = None
    language: Optional[str] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    media_id: Optional[str] = None
    transcription_id: Optional[str] = None
    user_id: Optional[str] = None


class AnalyzeTextCommandHandler:
    def __init__(
        self,
        sentiment_service: SentimentServicePort,
        embedding_service: EmbeddingServicePort,
        topic_modeling: TopicModelingPort,
        text_generation: TextGenerationPort,
        chunker: ChunkingServicePort,
        repository: AnalysisRepositoryPort,
        config: Optional[AnalysisConfig] = None,
        event_bus=None,
    ) -> None:
        self.sentiment_service = sentiment_service
        self.embedding_service = embedding_service
        self.topic_modeling = topic_modeling
        self.text_generation = text_generation
        self.chunker = chunker
        self.repository = repository
        self.config = config or AnalysisConfig()
        self.event_bus = event_bus

    def __call__(self, command: AnalyzeTextCommand) -> AnalysisResultDTO:
        language = command.language or self.config.language
        chunk_size = command.chunk_size or self.config.chunk_size
        chunk_overlap = command.chunk_overlap or self.config.chunk_overlap

        document = Document.from_payload(command.text, command.segments)
        analysis = Analysis.new(document)
        analysis.media_id = command.media_id
        analysis.transcription_id = command.transcription_id
        analysis.user_id = command.user_id

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
            except Exception as exc:  # pragma: no cover - event emit fallback
                logger.warning("text_analysis.event_emit_failed", error=str(exc))
        return analysis_to_dto(analysis)

    def _emit_completed_event(self, analysis: Analysis) -> None:
        from src.shared.events.domain_events import (
            SentimentAnalysisCompleted,
            SummarizationCompleted,
            TopicModelingCompleted,
        )

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

        # Summarization (if any text_generation occurred)
        summarization_event = SummarizationCompleted(
            analysis_id=analysis.id,
            transcription_id=getattr(analysis.document, "id", ""),
            media_id=getattr(analysis, "media_id", None),
            provider="text_analysis",
            status="success",
            correlation_id=getattr(analysis, "correlation_id", None),
        )
        self.event_bus.publish(summarization_event)

        # Topic modeling completion
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

    def _summarize_topics(
        self, topics: List[Topic], language: str
    ) -> List[Topic]:
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
            except Exception as exc:  # pragma: no cover - guarded fallback
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
