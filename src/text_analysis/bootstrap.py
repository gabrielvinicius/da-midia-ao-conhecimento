# src/text_analysis/bootstrap.py
"""Bootstrap module for the consolidated text analysis service.
"""
from types import SimpleNamespace

import structlog
from dependency_injector import providers
from sqlalchemy.ext.asyncio import AsyncSession

from src.text_analysis.application.services import TextAnalysisService
from src.text_analysis.sentiment_analysis.bootstrap import (
    build_sentiment_analysis_module,
)
from src.text_analysis.summarization.bootstrap import (
    SummarizationContainer,
    build_summarization_module,
)
from src.text_analysis.topic_modeling.bootstrap import (
    build_topic_modeling_module,
)

logger = structlog.get_logger(__name__)


class TextAnalysisModule(SimpleNamespace):
    """Container for the text analysis module's components."""

    service: TextAnalysisService
    summarization: SimpleNamespace
    sentiment: SimpleNamespace
    topic_modeling: SimpleNamespace


async def build_text_analysis_module(
    session: AsyncSession,
    *,
    media_module,
    notification_module,
    monitoring_module,
) -> TextAnalysisModule:
    """Builds and configures the text analysis module and its dependencies.
    """
    logger.info("text_analysis.bootstrap.started")

    text_analysis_service = TextAnalysisService()

    summarization_container = SummarizationContainer(
        text_analysis_service=providers.Object(text_analysis_service),
    )
    summarization_container.db.override(providers.Object(session))
    summarization_module = await build_summarization_module(summarization_container)

    connection_manager = getattr(notification_module.service, "connection_manager", None)
    sentiment_module = await build_sentiment_analysis_module(
        session=session,
        transcription_queries=media_module.transcription_queries,
        connection_manager=connection_manager,
        metrics_service=getattr(monitoring_module, "metrics_service", None),
        text_analysis_service=text_analysis_service,
    )

    topic_module = await build_topic_modeling_module(
        session=session,
        text_analysis_service=text_analysis_service,
    )

    logger.info("text_analysis.bootstrap.completed")

    return TextAnalysisModule(
        service=text_analysis_service,
        summarization=summarization_module,
        sentiment=sentiment_module,
        topic_modeling=topic_module,
    )
