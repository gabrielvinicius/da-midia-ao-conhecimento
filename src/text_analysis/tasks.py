from __future__ import annotations

import time
from typing import Any, Dict, Optional

import structlog
from celery import shared_task
from pydantic import ValidationError

# Imports for summarization tasks
from src.shared.infrastructure.database import get_sync_db
from src.text_analysis.application.domain_services import (
    SentimentAnalysisDomainService,
    SummarizationDomainService,
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
from dependency_injector import providers
from src.text_analysis.topic_modeling.bootstrap import TopicModelingContainer
from src.text_analysis.topic_modeling.infrastructure.metrics import NoOpTopicModelingMetrics
from src.storage.infrastructure.dependencies import StorageServiceFactory
from sqlalchemy.orm import Session

from src.shared.event_bus import InMemoryEventBus
from src.shared.events.domain_events import TextContentReady
from src.text_analysis.application.event_handlers import build_text_content_ready_handler
# Removido import circular: from src.text_analysis.application.services import TextAnalysisService

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
        return _run_text_processing_sync(payload)
    except Exception as e:
        logger.error(
            "text_processing.task_failed",
            extra={
                "media_id": media_id,
                "error": str(e),
            },
            exc_info=True,
        )
        return None

def _run_text_processing_sync(
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
        # Call the text processor's method synchronously
        result = processor.process_text_sync(
            text_content=payload.text_content,
            processing_type=payload.processing_type,
            options=payload.options,
        ) if hasattr(processor, 'process_text_sync') else processor.process_text(
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
        return _run_text_extraction_sync(payload)
    except Exception as e:
        logger.error(
            "text_extraction.task_failed",
            extra={
                "media_id": media_id,
                "error": str(e),
            },
            exc_info=True,
        )
        return None

def _run_text_extraction_sync(
    payload: TextExtractionPayload,
) -> Optional[Dict[str, Any]]:
    start_time = time.monotonic()
    success = False
    error = None

    storage_factory = StorageServiceFactory()

    from src.shared.infrastructure.database import get_sync_session
    with get_sync_session() as db:
        container = TextProcessingContainer(
            db=db,
            storage_factory=storage_factory,
            storage_provider=payload.storage_provider,
        )
        extractor: TextExtractor = container.text_extractor()
        # Call the extractor's method synchronously
        extracted_text = extractor.extract_text_sync(
            file_path=payload.file_path,
            extraction_method=payload.extraction_method,
            storage_provider=payload.storage_provider,
        ) if hasattr(extractor, 'extract_text_sync') else extractor.extract_text(
            file_path=payload.file_path,
            extraction_method=payload.extraction_method,
            storage_provider=payload.storage_provider,
        )

    logger.info(
        "text_processing.extract.started",
        media_id=str(payload.media_id),
        file_path=payload.file_path,
        extraction_method=payload.extraction_method,
        storage_provider=payload.storage_provider,
    )
    try:
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

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5, countdown=5)
def process_summarization_task(
        self,
        transcription_id: str,
        *,
        media_id: Optional[str] = None,
        text_content: str,
        provider: str = "builtin",
        options: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    try:
        payload = SummarizationTaskPayload.model_validate(
            {
                "transcription_id": transcription_id,
                "media_id": media_id,
                "text_content": text_content,
                "provider": provider,
                "options": options,
            }
        )
    except ValidationError as exc:
        logger.error(
            "summarization.task_invalid_payload",
            transcription_id=transcription_id,
            errors=exc.errors(),
        )
        return None

    try:
        # Use synchronous database session
        from src.shared.infrastructure.database import get_sync_session
        with get_sync_session() as db:
            return _run_summarization_sync(db, payload=payload)
    except Exception as e:
        logger.error(
            "summarization.task_failed",
            extra={
                "transcription_id": transcription_id,
                "error": str(e),
            },
            exc_info=True,
        )
        raise

def _run_summarization_sync(
    db: Session,
    *,
    payload: SummarizationTaskPayload,
) -> Optional[str]:
    logger.info(
        "summarization.task.start",
        transcription_id=str(payload.transcription_id),
        provider=payload.provider,
    )
    
    # Get the transcription text content for summarization
    from src.media_processing.transcription.infrastructure.transcription_repository import TranscriptionRepository
    transcription_repo = TranscriptionRepository(db)
    transcription = transcription_repo.get_by_id_sync(payload.transcription_id)

    if transcription is None:
        logger.error(
            "summarization.transcription_not_found",
            transcription_id=str(payload.transcription_id),
        )
        raise ValueError(f"No transcription found for ID: {payload.transcription_id}")

    text_content = transcription.text or getattr(transcription, 'content', '') or payload.text_content

    service = SummarizationDomainService(
        session=db,
        repository=SummarizationRepository(db),
        summarizer=TextRankSummarizer(),
    )

    db.commit()
    summary = service.generate_summary_sync(
        transcription_id=transcription.id,
        text_content=text_content,  # Use transcription text content
        provider=payload.provider,
        options=payload.options,
    )

    # Commit any pending changes to the database
    try:
        db.commit()
    except Exception as e:
        # If there's an issue with commit, make sure to rollback but don't fail the whole process
        try:
            db.rollback()
        except Exception:
            pass  # Just suppress rollback errors
        logger.warning(
            "summarization.database_commit_failed",
            transcription_id=payload.transcription_id,
            error=str(e),
        )

    logger.info(
        "summarization.task.completed",
        transcription_id=str(payload.transcription_id),
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
        language: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    try:
        payload = SentimentTaskPayload.model_validate(
            {
                "transcription_id": transcription_id,
                "text": text,
                "provider": provider,
                "model": model,
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
        # Use synchronous database session
        from src.shared.infrastructure.database import get_sync_session
        with get_sync_session() as db:
            return _run_sentiment_analysis_sync(db, payload)
    except Exception as e:
        logger.error(
            "sentiment_analysis.task_failed",
            extra={
                "transcription_id": transcription_id,
                "error": str(e),
            },
            exc_info=True,
        )
        return None

def _run_sentiment_analysis_sync(
    db: Session,
    payload: SentimentTaskPayload,
) -> Optional[Dict[str, Any]]:
    import time
    start_time = time.perf_counter()
    # Update import path to match what would be used in sync context
    from src.shared.config.settings import settings
    from src.text_analysis.sentiment_analysis.infrastructure.sentiment_analysis_repository import (
        SentimentAnalysisRepository,
    )
    from src.text_analysis.sentiment_analysis.infrastructure.sentiment_analyzer import (
        create_registry,
    )

    logger.info(
        "sentiment_analysis.started",
        transcription_id=str(payload.transcription_id),
        provider=payload.provider,
    )

    # Get the transcription text content if not provided directly
    if not payload.text:
        from src.media_processing.transcription.infrastructure.transcription_repository import TranscriptionRepository
        transcription_repo = TranscriptionRepository(db)
        transcription = transcription_repo.get_by_id_sync(payload.transcription_id)
        
        if transcription is None:
            logger.error(
                "sentiment_analysis.transcription_not_found",
                transcription_id=str(payload.transcription_id),
            )
            raise ValueError(f"No transcription found for ID: {payload.transcription_id}")
        
        payload.text = transcription.text or getattr(transcription, 'content', '') or ''

    registry = create_registry(
        enabled=settings.sentiment_enabled_list,
        default_provider=settings.SENTIMENT_DEFAULT_PROVIDER,
        plugin_modules=settings.sentiment_plugin_modules,
        overrides=settings.sentiment_provider_overrides,
    )

    service = SentimentAnalysisDomainService(
        session=db,
        repository=SentimentAnalysisRepository(db),
        provider_registry=registry,
    )

    try:
        result = service.analyze_sentiment_sync(
            transcription_id=str(payload.transcription_id),
            text=payload.text,
            provider=payload.provider,
            model=payload.model,
            language=payload.language,
        )
        
        # Ensure result is JSON serializable by converting object properties to simple values
        if result and hasattr(result, 'to_dict') and callable(getattr(result, 'to_dict')):
            # If the result has a to_dict method, use it
            result = result.to_dict()
        elif result and hasattr(result, '__dict__'):
            # If it's a complex object, extract only the primitive values
            result = {
                k: v for k, v in result.__dict__.items()
                if not callable(v) and not k.startswith('_') and not hasattr(v, '__dict__')
            }
        elif not isinstance(result, dict):
            # If result is not a dict, wrap it in one
            result = {"result": result}
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(
            "sentiment_analysis.failed",
            transcription_id=str(payload.transcription_id),
            provider=payload.provider,
            error=str(exc),
        )
        raise


    
    if isinstance(result, dict) and "processing_time" not in result:
        result["processing_time"] = time.perf_counter() - start_time

    # Commit any pending changes to the database
    try:
        db.commit()
    except Exception as e:
        # If there's an issue with commit, make sure to rollback but don't fail the whole process
        try:
            db.rollback()
        except Exception:
            pass  # Just suppress rollback errors
        logger.warning(
            "sentiment_analysis.database_commit_failed",
            transcription_id=payload.transcription_id,
            error=str(e),
        )

    logger.info(
        "sentiment_analysis.completed",
        transcription_id=str(payload.transcription_id),
        provider=payload.provider,
        duration=result.get("processing_time") if isinstance(result, dict) else None,
    )

    # Ensure result is JSON serializable by extracting only primitive values
    if result and hasattr(result, 'to_dict') and callable(getattr(result, 'to_dict')):
        # If the result has a to_dict method, use it
        result_dict = result.to_dict()
        return result_dict
    elif result and hasattr(result, '__dict__'):
        # If it's a complex object, extract only the primitive values
        result_dict = {
            k: v for k, v in result.__dict__.items()
            if not callable(v) and not k.startswith('_') and isinstance(v, (str, int, float, bool, list, dict, type(None)))
        }
        return result_dict
    elif isinstance(result, dict):
        # If result is already a dict, make sure it's JSON serializable
        serializable_result = {}
        for k, v in result.items():
            if isinstance(v, (str, int, float, bool, list, dict, type(None))):
                serializable_result[k] = v
            elif hasattr(v, '__dict__'):
                # For nested objects, extract only primitive values
                serializable_result[k] = {
                    attr_k: attr_v for attr_k, attr_v in v.__dict__.items()
                    if not callable(attr_v) and not attr_k.startswith('_') and isinstance(attr_v, (str, int, float, bool, list, dict, type(None)))
                }
            else:
                # For any other type, convert to string representation
                serializable_result[k] = str(v) if v is not None else None
        return serializable_result
    else:
        # If result is a simple type, return directly
        return result if isinstance(result, (str, int, float, bool, type(None))) else str(result)

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5, countdown=5)
def process_topic_modeling_task(
        self,
        transcription_id: str,
        text_content: str,
        provider: str,
        language: str,
        options: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    try:
        payload = TopicModelingTaskPayload.model_validate(
            {
                "transcription_id": transcription_id,
                "text_content": text_content,
                "provider": provider,
                "language": language,
                "options": options,
            }
        )
    except ValidationError as exc:
        logger.error(
            "topic_modeling.task_invalid_payload",
            transcription_id=transcription_id,
            errors=exc.errors(),
        )
        return None

    try:
        # Use synchronous database session
        from src.shared.infrastructure.database import get_sync_session
        with get_sync_session() as db:
            return _run_topic_modeling_sync(db, payload=payload)
    except Exception as e:
        logger.error(
            "topic_modeling.task_failed",
            extra={
                "transcription_id": transcription_id,
                "error": str(e),
            },
            exc_info=True,
        )
        raise

def _run_topic_modeling_sync(
    db: Session,
    *,
    payload: TopicModelingTaskPayload,
) -> Optional[Dict[str, Any]]:
    logger.info(
        "topic_modeling.analyze.started",
        transcription_id=str(payload.transcription_id),
        provider=payload.provider,
    )

    # Use sync repository and service
    from src.shared.config.settings import settings
    from src.text_analysis.topic_modeling.infrastructure.topic_modeling_repository import TopicModelingRepository
    from src.text_analysis.topic_modeling.application.topic_modeling_service import TopicModelingService
    from src.text_analysis.topic_modeling.infrastructure.topic_modeler import (
        create_registry,
    )

    repo = TopicModelingRepository(db)
    result = repo.get_by_transcription_id_sync(str(payload.transcription_id))

    if result is None:
        from src.text_analysis.topic_modeling.domain.topic_modeling import TopicModelingResult
        result = TopicModelingResult.create(transcription_id=payload.transcription_id, provider=payload.provider)
        result = repo.add_sync(result)  # Assign the returned value from add_sync

    # Get the transcription text content for topic modeling
    from src.media_processing.transcription.infrastructure.transcription_repository import TranscriptionRepository
    transcription_repo = TranscriptionRepository(db)
    transcription = transcription_repo.get_by_id_sync(payload.transcription_id)

    if transcription is None:
        logger.error(
            "topic_modeling.transcription_not_found",
            transcription_id=str(payload.transcription_id),
        )
        raise ValueError(f"No transcription found for ID: {payload.transcription_id}")

    text_content = transcription.text or getattr(transcription, 'content', '') or payload.text_content

    # Process the topic modeling using sync operations
    # Instantiate the service with proper dependencies
    from src.text_analysis.topic_modeling.infrastructure.topic_modeling_repository import TopicModelingRepository
    from src.text_analysis.topic_modeling.infrastructure.logging import StructuredTopicModelingLogger
    from src.text_analysis.topic_modeling.infrastructure.metrics import NoOpTopicModelingMetrics
    registry = create_registry(
        enabled=settings.topic_modeling_enabled_list,
        default_provider=settings.TOPIC_MODELING_DEFAULT_PROVIDER,
        plugin_modules=settings.topic_modeling_plugin_modules,
        overrides=settings.topic_modeling_provider_overrides,
    )

    service = TopicModelingService(
        topic_modeler_registry=registry,
        topic_modeling_repo=repo,
        text_analysis_service=None,
        topic_logger=StructuredTopicModelingLogger(),
        topic_metrics=NoOpTopicModelingMetrics(),
    )
    db.commit()
    analysis_result = service.analyze_topics_sync(
        media_id=transcription.media_id,
        transcription_id=transcription.id,
        text_content=text_content,  # Use transcription text content
        provider=payload.provider,
        language=payload.language,
        options=payload.options,
    )

    logger.info(
        "topic_modeling.analyze.completed",
        transcription_id=str(payload.transcription_id),
        result_id=str(analysis_result.id) if analysis_result and hasattr(analysis_result, 'id') else 'unknown',
    )

    # Ensure result is JSON serializable
    if analysis_result and hasattr(analysis_result, 'to_dict') and callable(getattr(analysis_result, 'to_dict')):
        # If result has to_dict method, use it
        result_dict = analysis_result.to_dict()
        final_result = {
            "success": True,
            "result_id": result_dict.get('id', 'unknown'),
            "topics": result_dict.get('topics', {}),
        }
    elif analysis_result and hasattr(analysis_result, '__dict__'):
        # If it's a complex object, extract only primitive values
        result_dict = {k: v for k, v in analysis_result.__dict__.items()
                      if not callable(v) and not k.startswith('_')}
        final_result = {
            "success": True,
            "result_id": result_dict.get('id', 'unknown'),
            "topics": result_dict.get('topics', {}),
        }
    elif analysis_result is None:
        # Handle case where analysis_result is None
        logger.warning(
            "topic_modeling.service_returned_none",
            transcription_id=payload.transcription_id,
            provider=payload.provider,
        )
        final_result = {
            "success": True,
            "result_id": "unknown",
            "topics": {},
        }
    else:
        # Fallback case
        final_result = {
            "success": True,
            "result_id": "unknown",
            "topics": {},
        }

    # Commit any pending changes to the database
    try:
        db.commit()
    except Exception as e:
        # If there's an issue with commit, make sure to rollback but don't fail the whole process
        try:
            db.rollback()
        except Exception:
            pass  # Just suppress rollback errors
        logger.warning(
            "topic_modeling.database_commit_failed",
            transcription_id=payload.transcription_id,
            error=str(e),
        )

    return final_result
