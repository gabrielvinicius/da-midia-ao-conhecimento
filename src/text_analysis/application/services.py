"""This module contains the TextAnalysisService, which orchestrates text-related operations.
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

import structlog

# Deixar os imports comentados para evitar importação circular
# Serão importados localmente dentro das funções conforme necessário
# from src.text_analysis.tasks import (
#     extract_text_task,
#     process_sentiment_analysis_task,
#     process_summarization_task,
#     process_text_task,
#     process_topic_modeling_task,
# )

logger = structlog.get_logger(__name__)

TaskCallable = Callable[..., Any]


@dataclass(slots=True)
class TextAnalysisTaskDispatcher:
    """Dispatches heavy workloads to the background execution layer (Celery by default)."""

    process_text: TaskCallable
    extract_text: TaskCallable
    summarize_text: TaskCallable
    sentiment_analysis: TaskCallable
    topic_modeling: TaskCallable

    def dispatch(self, task: TaskCallable, *args, **kwargs):
        return task(*args, **kwargs)


def _default_task_dispatcher() -> TextAnalysisTaskDispatcher:
    """Return a dispatcher wired to Celery `.delay` calls by default."""
    # Importar localmente para evitar importação circular
    from src.text_analysis.tasks import (
        process_text_task,
        extract_text_task,
        process_summarization_task,
        process_sentiment_analysis_task,
        process_topic_modeling_task,
    )
    return TextAnalysisTaskDispatcher(
        process_text=lambda *a, **kw: process_text_task.delay(*a, **kw),
        extract_text=lambda *a, **kw: extract_text_task.delay(*a, **kw),
        summarize_text=lambda *a, **kw: process_summarization_task.delay(*a, **kw),
        sentiment_analysis=lambda *a, **kw: process_sentiment_analysis_task.delay(*a, **kw),
        topic_modeling=lambda *a, **kw: process_topic_modeling_task.delay(*a, **kw),
    )


class TextAnalysisService:
    def __init__(self, dispatcher: Optional[TextAnalysisTaskDispatcher] = None):
        self._dispatcher = dispatcher or _default_task_dispatcher()

    def _submit(self, task: TaskCallable, *args, **kwargs) -> Any:
        return self._dispatcher.dispatch(task, *args, **kwargs)

    async def schedule_process_text_task(
        self,
        media_id: str,
        text_content: str,
        processing_type: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        logger.info(
            "text_analysis.scheduling_process_text_task",
            media_id=media_id,
            processing_type=processing_type,
        )
        # Importar localmente para evitar importação circular
        from src.text_analysis.tasks import process_text_task
        task = self._submit(
            self._dispatcher.process_text,
            media_id=media_id,
            text_content=text_content,
            processing_type=processing_type,
            options=options,
        )
        logger.info(
            "text_analysis.process_text_task_scheduled",
            media_id=media_id,
            task_id=getattr(task, "id", None),
        )
        return {"task_id": getattr(task, "id", None)}

    async def schedule_extract_text_task(
        self,
        media_id: str,
        file_path: str,
        extraction_method: str,
        storage_provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        logger.info(
            "text_analysis.scheduling_extract_text_task",
            media_id=media_id,
            file_path=file_path,
            extraction_method=extraction_method,
        )
        # Importar localmente para evitar importação circular
        from src.text_analysis.tasks import extract_text_task
        task = self._submit(
            self._dispatcher.extract_text,
            media_id=media_id,
            file_path=file_path,
            extraction_method=extraction_method,
            storage_provider=storage_provider,
        )
        logger.info(
            "text_analysis.extract_text_task_scheduled",
            media_id=media_id,
            task_id=getattr(task, "id", None),
        )
        return {"task_id": getattr(task, "id", None)}

    async def schedule_summarization_task(
        self,
        *,
        transcription_id: str,
        media_id: Optional[str],
        text_content: str,
        provider: str = "builtin",
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        logger.info(
            "text_analysis.scheduling_summarization_task",
            transcription_id=transcription_id,
            media_id=media_id,
            provider=provider,
        )
        # Importar localmente para evitar importação circular
        from src.text_analysis.tasks import process_summarization_task
        task = self._submit(
            self._dispatcher.summarize_text,
            transcription_id=transcription_id,
            media_id=media_id,
            text_content=text_content,
            provider=provider,
            options=options,
        )
        logger.info(
            "text_analysis.summarization_task_scheduled",
            transcription_id=transcription_id,
            task_id=getattr(task, "id", None),
        )
        return {"task_id": getattr(task, "id", None)}

    async def schedule_sentiment_analysis_task(
        self,
        transcription_id: str,
        text: str,
        provider: str,
        model: Optional[str] = None,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        logger.info(
            "text_analysis.scheduling_sentiment_analysis_task",
            transcription_id=transcription_id,
            provider=provider,
        )
        # Importar localmente para evitar importação circular
        from src.text_analysis.tasks import process_sentiment_analysis_task
        task = self._submit(
            self._dispatcher.sentiment_analysis,
            transcription_id=transcription_id,
            text=text,
            provider=provider,
            model=model,
            language=language,
        )
        logger.info(
            "text_analysis.sentiment_analysis_task_scheduled",
            transcription_id=transcription_id,
            task_id=getattr(task, "id", None),
        )
        return {"task_id": getattr(task, "id", None)}

    async def schedule_topic_modeling_task(
        self,
        transcription_id: str,
        text_content: str,
        provider: str,
        language: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        logger.info(
            "text_analysis.scheduling_topic_modeling_task",
            transcription_id=transcription_id,
            provider=provider,
        )
        # Importar localmente para evitar importação circular
        from src.text_analysis.tasks import process_topic_modeling_task
        task = self._submit(
            self._dispatcher.topic_modeling,
            transcription_id=transcription_id,
            text_content=text_content,
            provider=provider,
            language=language,
            options=options,
        )
        logger.info(
            "text_analysis.topic_modeling_task_scheduled",
            transcription_id=transcription_id,
            task_id=getattr(task, "id", None),
        )
        return {"task_id": getattr(task, "id", None)}
