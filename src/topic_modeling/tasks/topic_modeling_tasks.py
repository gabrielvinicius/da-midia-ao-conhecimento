# src/topic_modeling/tasks/topic_modeling_tasks.py
import asyncio
import structlog
from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional

from src.shared.infrastructure.database import get_db
from src.topic_modeling.application.commands.commands import AnalyzeTopicsCommand
from src.topic_modeling.application.commands.handlers import AnalyzeTopicsCommandHandler
from src.topic_modeling.bootstrap import TopicModelingContainer

logger = structlog.get_logger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def analyze_topics_task(self, media_id: str, text_content: str, provider: str, language: str, options: Optional[Dict[str, Any]] = None):
    """Celery entrypoint to trigger the topic modeling pipeline."""
    try:
        return asyncio.run(_run_topic_modeling(media_id, text_content, provider, language, options))
    except Exception as e:
        logger.error(f"Error in topic modeling task for media {media_id}: {str(e)}", exc_info=True)
        return None


async def _run_topic_modeling(media_id: str, text_content: str, provider: str, language: str, options: Optional[Dict[str, Any]] = None):
    """Helper to run topic modeling logic with dependency injection."""
    async for db_session in get_db():
        if not isinstance(db_session, AsyncSession):
            raise TypeError("Expected db_session to be an AsyncSession")

        # --- Dependency Injection using Container ---
        topic_modeling_container = TopicModelingContainer()
        topic_modeling_container.db.override(db_session) # Sobrescrever a dependência do DB

        # 1. Create the command handler (resolved from container)
        handler: AnalyzeTopicsCommandHandler = topic_modeling_container.analyze_topics_command_handler()

        # 2. Create the command
        command = AnalyzeTopicsCommand(
            media_id=media_id,
            text_content=text_content,
            provider=provider,
            language=language,
            options=options
        )

        # 3. Execute the handler
        try:
            return await handler.handle(command)
        except Exception as e:
            logger.error(f"Error processing topic modeling for media {media_id}: {str(e)}", exc_info=True)
            raise
