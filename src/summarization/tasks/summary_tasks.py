import asyncio
import structlog
from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.infrastructure.database import get_db
from src.shared.events.event_bus import get_event_bus

# Import CQRS components and their dependencies
from src.summarization.application.commands.process_summary_command import ProcessSummaryCommand
from src.summarization.application.commands.process_summary_command_handler import ProcessSummaryCommandHandler
from src.summarization.infrastructure.dependencies import create_summarizer_service
from src.summarization.infrastructure.summary_repository import SummaryRepository
from src.transcription.application.queries.transcription_queries import TranscriptionQueries
from src.transcription.infrastructure.transcription_repository import TranscriptionRepository
from src.analytics.application.queries.analytics_queries import AnalyticsQueries
from src.analytics.infrastructure.analytics_repository import AnalyticsRepository
from src.analytics.config.settings import AnalyticsSettings
from src.metrics.application.metrics_service import MetricsService
from src.metrics.infrastructure.prometheus_provider import PrometheusMetricsProvider

logger = structlog.get_logger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def process_summary_task(self, transcription_id: str, provider: str):
    """Celery entrypoint to trigger the summarization pipeline with a specific provider."""
    try:
        return asyncio.run(_run_summarization(transcription_id, provider))
    except Exception as e:
        logger.error(f"Error in summarization task for transcription {transcription_id}: {str(e)}", exc_info=True)
        return None


async def _run_summarization(transcription_id: str, provider: str):
    """Helper to run summarization logic with dynamic dependency injection."""
    async for db_session in get_db():
        if not isinstance(db_session, AsyncSession):
            raise TypeError("Expected db_session to be an AsyncSession")

        # --- Manual Dependency Injection for Celery Task ---
        event_bus = get_event_bus()
        metrics_service = MetricsService(provider=PrometheusMetricsProvider())
        
        # Build necessary query services and repositories
        transcription_repo = TranscriptionRepository(db=db_session)
        transcription_queries = TranscriptionQueries(transcription_repository=transcription_repo)
        
        analytics_repo = AnalyticsRepository(db=db_session)
        analytics_settings = AnalyticsSettings()
        analytics_queries = AnalyticsQueries(analytics_repo=analytics_repo, settings=analytics_settings)

        summary_repo = SummaryRepository(db=db_session)
        summarizer_instance = create_summarizer_service(provider)

        # 1. Create the command handler
        handler = ProcessSummaryCommandHandler(
            summarizer=summarizer_instance,
            summary_repo=summary_repo,
            transcription_queries=transcription_queries,
            metrics_service=metrics_service,
            analytics_queries=analytics_queries,
            event_bus=event_bus
        )

        # 2. Create the command
        command = ProcessSummaryCommand(
            transcription_id=transcription_id,
            provider=provider
        )

        # 3. Execute the handler
        try:
            return await handler.handle(command)
        except Exception as e:
            logger.error(f"Error processing summarization for transcription {transcription_id}: {str(e)}", exc_info=True)
            raise
