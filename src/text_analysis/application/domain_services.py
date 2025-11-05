"""Domain-level services for text analysis operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.text_analysis.sentiment_analysis.domain.sentiment_analysis import (
    SentimentAnalysis,
)
from src.text_analysis.sentiment_analysis.infrastructure.sentiment_analysis_repository import (
    SentimentAnalysisRepository,
)
from src.text_analysis.summarization.domain.model.summary_aggregate import (
    SummaryAggregate,
)
from src.text_analysis.summarization.infrastructure.summarization_repository import (
    SummarizationRepository,
)
from src.text_analysis.summarization.infrastructure.summarizer import TextRankSummarizer
from src.text_analysis.topic_modeling.domain.topic_modeling import TopicModelingResult
from src.text_analysis.topic_modeling.infrastructure.logging import (
    StructuredTopicModelingLogger,
)
from src.text_analysis.topic_modeling.infrastructure.metrics import (
    PrometheusTopicModelingMetrics,
)
from src.text_analysis.topic_modeling.infrastructure.topic_modeling_repository import (
    TopicModelingRepository,
)

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class SummarizationDomainService:
    """Handle summarization lifecycle without Celery-specific concerns."""

    session: AsyncSession
    repository: SummarizationRepository
    summarizer: TextRankSummarizer

    async def generate_summary(
        self,
        *,
        media_id: UUID,
        text_content: str,
        provider: str = "builtin",
        options: Optional[Dict[str, Any]] = None,
    ) -> SummaryAggregate:
        summary = await self.repository.get_by_media_id(media_id)
        if summary is None:
            summary = SummaryAggregate.create(media_id=media_id, provider=provider)
            summary = await self.repository.add(summary)
        else:
            summary = summary.with_provider(provider).mark_processing()
            summary = await self.repository.update(summary)

        try:
            summary_text = await self.summarizer.summarize(text_content, options)
            summary = summary.mark_as_completed(summary_text)
            summary = await self.repository.update(summary)
            await self.session.commit()
            logger.info(
                "summarization.domain.completed",
                media_id=str(media_id),
                summary_id=str(summary.id),
            )
            return summary
        except Exception as exc:
            summary = summary.mark_as_failed(str(exc))
            await self.repository.update(summary)
            await self.session.commit()
            logger.error(
                "summarization.domain.failed",
                media_id=str(media_id),
                error=str(exc),
                exc_info=True,
            )
            raise


@dataclass(slots=True)
class SentimentAnalysisDomainService:
    """Process sentiment analysis results using repository persistence."""

    session: AsyncSession
    repository: SentimentAnalysisRepository
    analyzer: Any

    async def analyze_sentiment(
        self,
        *,
        transcription_id: str,
        text: str,
        provider: str,
        model: Optional[str] = None,
        media_id: Optional[str] = None,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        analysis = await self.repository.find_by_transcription_id(transcription_id)
        if analysis is None:
            analysis = SentimentAnalysis(
                transcription_id=transcription_id,
                media_id=media_id,
                provider=provider,
                model=model,
            )

        payload = await self.analyzer.analyze(
            text=text,
            provider=provider,
            model=model,
            language=language,
        )

        analysis.update_from_payload(payload)
        analysis.provider = provider
        analysis.model = model
        if media_id is not None:
            analysis.media_id = media_id

        saved = await self.repository.save(analysis)
        await self.session.commit()

        logger.info(
            "sentiment_analysis.domain.completed",
            transcription_id=transcription_id,
            provider=provider,
        )

        response = {
            "success": True,
            "analysis": saved,
            "provider": provider,
            "model": model,
            "processing_time": payload.get("processing_time"),
        }
        response.update({k: v for k, v in payload.items() if k not in response})
        return response


@dataclass(slots=True)
class TopicModelingDomainService:
    """Execute topic modeling operations via repository and instrumentation."""

    session: AsyncSession
    repository: TopicModelingRepository
    modeler: Any
    operation_logger: StructuredTopicModelingLogger
    metrics: PrometheusTopicModelingMetrics

    async def analyze_topics(
        self,
        *,
        media_id: UUID,
        text_content: str,
        provider: str,
        language: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> TopicModelingResult:
        import time

        start_time = time.monotonic()
        result: Optional[TopicModelingResult] = None
        success = False
        error: Optional[Exception] = None

        try:
            modeling_data = await self.modeler.model_topics(
                text_content=text_content,
                language=language,
                options=options,
            )

            result = await self.repository.get_by_media_id(media_id)
            if result is None:
                result = TopicModelingResult.create(media_id=media_id, provider=provider)
                await self.repository.add(result)

            result.mark_as_completed(modeling_data.get("topics", {}))
            await self.repository.update(result)
            await self.session.commit()
            success = True
            return result
        except Exception as exc:  # pragma: no cover - defensive logging
            error = exc
            if result is None:
                result = TopicModelingResult.create(media_id=media_id, provider=provider)
                result.mark_as_failed(str(exc))
                await self.repository.add(result)
            else:
                result.mark_as_failed(str(exc))
                await self.repository.update(result)
            await self.session.commit()
            logger.error(
                "topic_modeling.domain.failed",
                media_id=str(media_id),
                provider=provider,
                error=str(exc),
                exc_info=True,
            )
            raise
        finally:
            duration = time.monotonic() - start_time
            await self.operation_logger.log_operation(
                operation="analyze_topics",
                media_id=str(media_id),
                provider=provider,
                success=success,
                duration=duration,
                error=error,
            )
            await self.metrics.record_operation(
                operation="analyze_topics",
                provider=provider,
                duration=duration,
                success=success,
            )


__all__ = [
    "SummarizationDomainService",
    "SentimentAnalysisDomainService",
    "TopicModelingDomainService",
]
