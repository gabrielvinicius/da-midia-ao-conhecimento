from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List, Optional
from uuid import UUID
import time

import structlog
from celery import shared_task

# Imports for text processing tasks
from src.text_analysis.text_processing.infrastructure.text_processor import TextProcessor
from src.text_analysis.text_processing.infrastructure.text_extractor import TextExtractor

# Imports for summarization tasks
from src.shared.infrastructure.database import get_db
from src.text_analysis.summarization.domain.summary import Summary
from src.text_analysis.summarization.infrastructure.summarization_repository import SummarizationRepository
from src.text_analysis.summarization.infrastructure.summarizer import TextRankSummarizer

# Imports for topic modeling tasks
from src.text_analysis.topic_modeling.domain.topic_modeling import TopicModelingResult
from src.text_analysis.topic_modeling.infrastructure.topic_modeling_repository import TopicModelingRepository
from src.text_analysis.topic_modeling.infrastructure.topic_modeler import BERTopicModeler
from src.text_analysis.topic_modeling.infrastructure.logging import StructuredTopicModelingLogger
from src.text_analysis.topic_modeling.infrastructure.metrics import PrometheusTopicModelingMetrics

logger = structlog.get_logger(__name__)

@shared_task
def placeholder_text_analysis_task():
    """Placeholder task for text analysis."""
    pass

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def process_text_task(
        self,
        media_id: str,
        text_content: str,
        processing_type: str,
        options: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    try:
        return asyncio.run(
            _run_text_processing(media_id, text_content, processing_type, options)
        )
    except Exception as e:
        logger.error(
            "text_processing.task_failed",
            media_id=media_id,
            error=str(e),
            exc_info=True,
        )
        return None

async def _run_text_processing(
    media_id: str,
    text_content: str,
    processing_type: str,
    options: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    start_time = time.monotonic()
    success = False
    error = None

    # TODO: Resolve dependencies via DI container later
    processor = TextProcessor()

    logger.info("text_processing.process.started", media_id=media_id, processing_type=processing_type)
    try:
        result = await processor.process_text(
            text_content=text_content,
            processing_type=processing_type,
            options=options
        )
        success = True
        logger.info("text_processing.process.completed", media_id=media_id)
        return {
            "success": True,
            "media_id": media_id,
            "processing_type": processing_type,
            "message": "Text processing completed successfully",
            "result": result
        }
    except Exception as e:
        error = e
        logger.error("text_processing.process.failed", media_id=media_id, error=str(e))
        raise
    finally:
        duration = time.monotonic() - start_time
        # TODO: Adicionar logging e métricas aqui

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def extract_text_task(
        self,
        media_id: str,
        file_path: str,
        extraction_method: str,
) -> Optional[Dict[str, Any]]:
    try:
        return asyncio.run(
            _run_text_extraction(media_id, file_path, extraction_method)
        )
    except Exception as e:
        logger.error(
            "text_extraction.task_failed",
            media_id=media_id,
            error=str(e),
            exc_info=True,
        )
        return None

async def _run_text_extraction(
    media_id: str,
    file_path: str,
    extraction_method: str,
) -> Optional[Dict[str, Any]]:
    start_time = time.monotonic()
    success = False
    error = None

    # TODO: Resolve dependencies via DI container later
    extractor = TextExtractor()

    logger.info("text_processing.extract.started", media_id=media_id, file_path=file_path, extraction_method=extraction_method)
    try:
        extracted_text = await extractor.extract_text(
            file_path=file_path,
            extraction_method=extraction_method
        )
        success = True
        logger.info("text_processing.extract.completed", media_id=media_id)
        return {
            "success": True,
            "media_id": media_id,
            "extraction_method": extraction_method,
            "message": "Text extraction completed successfully",
            "extracted_text": extracted_text
        }
    except Exception as e:
        error = e
        logger.error("text_processing.extract.failed", media_id=media_id, error=str(e))
        raise
    finally:
        duration = time.monotonic() - start_time
        # TODO: Adicionar logging e métricas aqui


def _ensure_uuid(value: UUID | str) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def process_summarization_task(
        self,
        media_id: str,
        text_content: str,
        provider: str = "builtin",
        options: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    try:
        return asyncio.run(
            _run_summarization(media_id, text_content, provider, options)
        )
    except Exception as e:
        logger.error(
            "summarization.task_failed",
            media_id=media_id,
            error=str(e),
            exc_info=True,
        )
        return None

async def _run_summarization(
    media_id: str,
    text_content: str,
    provider: str,
    options: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    media_uuid = _ensure_uuid(media_id)
    async for db in get_db():
        # TODO: Resolve dependencies via DI container later
        repo = SummarizationRepository(db)
        summarizer = TextRankSummarizer()

        logger.info("summarization.task.start", media_id=media_id, provider=provider)

        existing = await repo.get_by_media_id(media_uuid)

        summary = (
            existing.with_provider(provider).mark_processing()
            if existing
            else Summary.create(media_id=media_uuid, provider=provider)
        )

        if existing is None:
            summary = await repo.add(summary)

        try:
            summary_text = await summarizer.summarize(text_content, options)
            completed = summary.mark_as_completed(summary_text)
            await repo.update(completed)
            await db.commit()

            logger.info(
                "summarization.task.completed",
                media_id=media_id,
                summary_id=str(summary.id),
            )
            return str(summary.id)
        except Exception as exc:
            logger.error(
                "summarization.task.error",
                media_id=media_id,
                error=str(exc),
                exc_info=True,
            )
            summary.mark_as_failed(str(exc))
            await repo.update(summary)
            await db.commit()
            raise

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def process_sentiment_analysis_task(
        self,
        transcription_id: str,
        text: str,
        provider: str,
        model: Optional[str] = None,
        media_id: Optional[str] = None,
        language: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    try:
        return asyncio.run(
            _run_sentiment_analysis(transcription_id, text, provider, model, media_id, language)
        )
    except Exception as e:
        logger.error(
            "sentiment_analysis.task_failed",
            transcription_id=transcription_id,
            error=str(e),
            exc_info=True,
        )
        return None

async def _run_sentiment_analysis(
    transcription_id: str,
    text: str,
    provider: str,
    model: Optional[str] = None,
    media_id: Optional[str] = None,
    language: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    start_time = time.perf_counter()
    # TODO: Resolve dependencies via DI container later
    from src.text_analysis.sentiment_analysis.application.sentiment_analysis_service import (
        SentimentAnalysisService,
    )  # local import to avoid circular dependency
    from src.text_analysis.sentiment_analysis.infrastructure.sentiment_analyzer import (
        HuggingFaceSentimentAnalyzer,
    )
    from src.text_analysis.sentiment_analysis.infrastructure.sentiment_analysis_repository import (
        SentimentAnalysisRepository,
    )

    analyzer = HuggingFaceSentimentAnalyzer()  # Placeholder, will be dynamic
    repository = SentimentAnalysisRepository()  # Placeholder, will be dynamic
    service = SentimentAnalysisService(analyzer=analyzer, repository=repository)

    logger.info("sentiment_analysis.started", transcription_id=transcription_id, provider=provider)

    try:
        payload = await service.analyze_sentiment(
            transcription_id=transcription_id,
            text=text,
            provider=provider,
            model=model,
            media_id=media_id,
            language=language,
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(
            "sentiment_analysis.failed",
            level="error",
            transcription_id=transcription_id,
            provider=provider,
            error=str(exc),
        )
        raise

    duration = time.perf_counter() - start_time
    payload.setdefault("provider", provider)
    payload.setdefault("model", model)
    payload.setdefault("media_id", media_id)
    payload.setdefault("processing_time", duration)

    # TODO: Record metrics and log operation via injected dependencies
    logger.info(
        "sentiment_analysis.completed",
        transcription_id=transcription_id,
        provider=provider,
        duration=duration,
    )

    return payload

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def process_topic_modeling_task(
        self,
        media_id: str,
        text_content: str,
        provider: str,
        language: str,
        options: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    try:
        return asyncio.run(
            _run_topic_modeling(media_id, text_content, provider, language, options)
        )
    except Exception as e:
        logger.error(
            "topic_modeling.task_failed",
            media_id=media_id,
            error=str(e),
            exc_info=True,
        )
        return None

async def _run_topic_modeling(
    media_id: str,
    text_content: str,
    provider: str,
    language: str,
    options: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    start_time = time.monotonic()
    success = False
    error = None
    result_id = None
    num_topics = 0

    media_uuid = UUID(media_id)
    async for db in get_db():
        # TODO: Resolve dependencies via DI container later
        modeler = BERTopicModeler() # Placeholder, will be dynamic
        repo = TopicModelingRepository(db) # Placeholder, will be dynamic
        topic_logger = StructuredTopicModelingLogger() # Placeholder, will be dynamic
        topic_metrics = PrometheusTopicModelingMetrics() # Placeholder, will be dynamic

        logger.info("topic_modeling.analyze.started", media_id=media_id, provider=provider)
        try:
            # 1. Perform topic modeling
            modeling_data = await modeler.model_topics(
                text_content=text_content,
                language=language,
                options=options
            )
            num_topics = modeling_data.get("num_topics", 0)

            # 2. Create or update TopicModelingResult entity
            existing_result = await repo.get_by_media_id(media_uuid)

            if existing_result:
                existing_result.mark_as_completed(modeling_data.get("topics", {}))
                await repo.update(existing_result)
                topic_result = existing_result
            else:
                topic_result = TopicModelingResult.create(
                    media_id=media_uuid,
                    provider=provider
                )
                topic_result.mark_as_completed(modeling_data.get("topics", {}))
                await repo.add(topic_result)
            
            result_id = topic_result.id
            success = True

            logger.info("topic_modeling.analyze.completed", media_id=media_id, result_id=str(result_id))
            return {"success": True, "result_id": str(result_id), "topics": modeling_data.get("topics", {})}

        except Exception as e:
            error = e
            logger.error("topic_modeling.analyze.failed", media_id=media_id, error=str(e))
            raise
        finally:
            duration = time.monotonic() - start_time
            await topic_logger.log_operation(
                operation="analyze_topics",
                media_id=media_id,
                provider=provider,
                success=success,
                duration=duration,
                error=error
            )
            await topic_metrics.record_operation(
                operation="analyze_topics",
                provider=provider,
                duration=duration,
                success=success,
                input_text_length_chars=len(text_content),
                num_topics=num_topics
            )
