from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional

import structlog
from celery import shared_task
from pydantic import ValidationError

# Imports for summarization tasks
from src.shared.infrastructure.database import get_db
from src.text_analysis.application.domain_services import (
    SentimentAnalysisDomainService,
    SummarizationDomainService,
    TopicModelingDomainService,
)
from src.text_analysis.summarization.infrastructure.summarization_repository import (
    SummarizationRepository,
)
from src.text_analysis.application.schemas import (
    SentimentTaskPayload,
    SummarizationTaskPayload,
    TextExtractionPayload,
    TextProcessPayload,
    TopicModelingTaskPayload,
)
from src.text_analysis.summarization.infrastructure.summarizer import TextRankSummarizer
from src.text_analysis.text_processing.bootstrap import TextProcessingContainer
from src.text_analysis.text_processing.infrastructure.text_extractor import (
    TextExtractor,
)

# Imports for text processing tasks
from src.text_analysis.text_processing.infrastructure.text_processor import (
    TextProcessor,
)
from src.text_analysis.topic_modeling.infrastructure.logging import (
    StructuredTopicModelingLogger,
)
from src.text_analysis.topic_modeling.infrastructure.metrics import (
    PrometheusTopicModelingMetrics,
)
from src.text_analysis.topic_modeling.infrastructure.topic_modeler import (
    BERTopicModeler,
)

# Imports for topic modeling tasks
from src.text_analysis.topic_modeling.infrastructure.topic_modeling_repository import (
    TopicModelingRepository,
)
from src.storage.infrastructure.dependencies import StorageServiceFactory

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
        payload = TextProcessPayload.model_validate(
            {
                "media_id": media_id,
                "text_content": text_content,
                "processing_type": processing_type,
                "options": options,
            }
        )
    except ValidationError as exc:
        logger.error(
            "text_processing.task_invalid_payload",
            media_id=media_id,
            errors=exc.errors(),
        )
        return None

    try:
        return asyncio.run(
            _run_text_processing(payload)
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
    payload: TextProcessPayload,
) -> Optional[Dict[str, Any]]:
    start_time = time.monotonic()
    success = False
    error = None

    # TODO: Resolve dependencies via DI container later
    processor = TextProcessor()

    logger.info(
        "text_processing.process.started",
        media_id=str(payload.media_id),
        processing_type=payload.processing_type,
    )
    try:
        result = await processor.process_text(
            text_content=payload.text_content,
            processing_type=payload.processing_type,
            options=payload.options,
        )
        success = True
        logger.info("text_processing.process.completed", media_id=str(payload.media_id))
        return {
            "success": True,
            "media_id": str(payload.media_id),
            "processing_type": payload.processing_type,
            "message": "Text processing completed successfully",
            "result": result
        }
    except Exception as e:
        error = e
        logger.error(
            "text_processing.process.failed",
            media_id=str(payload.media_id),
            error=str(e),
        )
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
        storage_provider: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    try:
        payload = TextExtractionPayload.model_validate(
            {
                "media_id": media_id,
                "file_path": file_path,
                "storage_provider": storage_provider or "local",
                "extraction_method": extraction_method,
            }
        )
    except ValidationError as exc:
        logger.error(
            "text_extraction.task_invalid_payload",
            media_id=media_id,
            errors=exc.errors(),
        )
        return None

    try:
        return asyncio.run(
            _run_text_extraction(payload)
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
    payload: TextExtractionPayload,
) -> Optional[Dict[str, Any]]:
    start_time = time.monotonic()
    success = False
    error = None

    storage_factory = StorageServiceFactory()

    async for db in get_db():
        container = TextProcessingContainer(
            db=db,
            storage_factory=storage_factory,
            storage_provider=payload.storage_provider,
        )
        extractor: TextExtractor = container.text_extractor()
        break
    else:  # pragma: no cover - generator should always yield
        raise RuntimeError("Database session not available for text extraction")

    logger.info(
        "text_processing.extract.started",
        media_id=str(payload.media_id),
        file_path=payload.file_path,
        extraction_method=payload.extraction_method,
        storage_provider=payload.storage_provider,
    )
    try:
        extracted_text = await extractor.extract_text(
            file_path=payload.file_path,
            extraction_method=payload.extraction_method,
            storage_provider=payload.storage_provider,
        )
        success = True
        logger.info("text_processing.extract.completed", media_id=str(payload.media_id))
        return {
            "success": True,
            "media_id": str(payload.media_id),
            "extraction_method": payload.extraction_method,
            "message": "Text extraction completed successfully",
            "extracted_text": extracted_text
        }
    except Exception as e:
        error = e
        logger.error(
            "text_processing.extract.failed",
            media_id=str(payload.media_id),
            error=str(e),
        )
        raise
    finally:
        duration = time.monotonic() - start_time
        # TODO: Adicionar logging e métricas aqui

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def process_summarization_task(
        self,
        media_id: str,
        text_content: str,
        provider: str = "builtin",
        options: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    try:
        payload = SummarizationTaskPayload.model_validate(
            {
                "media_id": media_id,
                "text_content": text_content,
                "provider": provider,
                "options": options,
            }
        )
    except ValidationError as exc:
        logger.error(
            "summarization.task_invalid_payload",
            media_id=media_id,
            errors=exc.errors(),
        )
        return None

    try:
        return asyncio.run(_run_summarization(payload=payload))
    except Exception as e:
        logger.error(
            "summarization.task_failed",
            media_id=media_id,
            error=str(e),
            exc_info=True,
        )
        return None

async def _run_summarization(
    *,
    payload: SummarizationTaskPayload,
) -> Optional[str]:
    async for db in get_db():
        logger.info(
            "summarization.task.start",
            media_id=str(payload.media_id),
            provider=payload.provider,
        )
        service = SummarizationDomainService(
            session=db,
            repository=SummarizationRepository(db),
            summarizer=TextRankSummarizer(),
        )

        summary = await service.generate_summary(
            media_id=payload.media_id,
            text_content=payload.text_content,
            provider=payload.provider,
            options=payload.options,
        )

        logger.info(
            "summarization.task.completed",
            media_id=str(payload.media_id),
            summary_id=str(summary.id),
        )
        return str(summary.id)

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
        payload = SentimentTaskPayload.model_validate(
            {
                "transcription_id": transcription_id,
                "text": text,
                "provider": provider,
                "model": model,
                "media_id": media_id,
                "language": language,
            }
        )
    except ValidationError as exc:
        logger.error(
            "sentiment_analysis.task_invalid_payload",
            transcription_id=transcription_id,
            errors=exc.errors(),
        )
        return None

    try:
        return asyncio.run(_run_sentiment_analysis(payload))
    except Exception as e:
        logger.error(
            "sentiment_analysis.task_failed",
            transcription_id=transcription_id,
            error=str(e),
            exc_info=True,
        )
        return None

async def _run_sentiment_analysis(
    payload: SentimentTaskPayload,
) -> Optional[Dict[str, Any]]:
    start_time = time.perf_counter()
    # TODO: Resolve dependencies via DI container later
    from src.text_analysis.sentiment_analysis.infrastructure.sentiment_analysis_repository import (
        SentimentAnalysisRepository,
    )
    from src.text_analysis.sentiment_analysis.infrastructure.sentiment_analyzer import (
        SimpleSentimentAnalyzer,
    )

    logger.info(
        "sentiment_analysis.started",
        transcription_id=str(payload.transcription_id),
        provider=payload.provider,
    )

    async for db in get_db():
        service = SentimentAnalysisDomainService(
            session=db,
            repository=SentimentAnalysisRepository(db),
            analyzer=SimpleSentimentAnalyzer(),
        )

        try:
            result = await service.analyze_sentiment(
                transcription_id=str(payload.transcription_id),
                text=payload.text,
                provider=payload.provider,
                model=payload.model,
                media_id=str(payload.media_id) if payload.media_id is not None else None,
                language=payload.language,
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.error(
                "sentiment_analysis.failed",
                transcription_id=str(payload.transcription_id),
                provider=payload.provider,
                error=str(exc),
            )
            raise

        if payload.media_id is not None:
            result.setdefault("media_id", str(payload.media_id))
        if "processing_time" not in result:
            result["processing_time"] = time.perf_counter() - start_time

        logger.info(
            "sentiment_analysis.completed",
            transcription_id=str(payload.transcription_id),
            provider=payload.provider,
            duration=result.get("processing_time"),
        )

        return result

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
        payload = TopicModelingTaskPayload.model_validate(
            {
                "media_id": media_id,
                "text_content": text_content,
                "provider": provider,
                "language": language,
                "options": options,
            }
        )
    except ValidationError as exc:
        logger.error(
            "topic_modeling.task_invalid_payload",
            media_id=media_id,
            errors=exc.errors(),
        )
        return None

    try:
        return asyncio.run(_run_topic_modeling(payload=payload))
    except Exception as e:
        logger.error(
            "topic_modeling.task_failed",
            media_id=media_id,
            error=str(e),
            exc_info=True,
        )
        return None

async def _run_topic_modeling(
    *,
    payload: TopicModelingTaskPayload,
) -> Optional[Dict[str, Any]]:
    async for db in get_db():
        logger.info(
            "topic_modeling.analyze.started",
            media_id=str(payload.media_id),
            provider=payload.provider,
        )

        service = TopicModelingDomainService(
            session=db,
            repository=TopicModelingRepository(db),
            modeler=BERTopicModeler(),
            operation_logger=StructuredTopicModelingLogger(),
            metrics=PrometheusTopicModelingMetrics(),
        )

        result = await service.analyze_topics(
            media_id=payload.media_id,
            text_content=payload.text_content,
            provider=payload.provider,
            language=payload.language,
            options=payload.options,
        )

        logger.info(
            "topic_modeling.analyze.completed",
            media_id=str(payload.media_id),
            result_id=str(result.id),
        )
        return {
            "success": True,
            "result_id": str(result.id),
            "topics": getattr(result, "topics", {}),
        }
