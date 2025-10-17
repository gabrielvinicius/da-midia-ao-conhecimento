# src/summarization/application/commands/process_summary_command_handler.py
import time
import structlog

from src.analytics.application.queries.analytics_queries import AnalyticsQueries
from src.shared.events.domain_events import SummarizationProgress
from src.shared.events.event_bus import EventBus
from src.media_management.application.queries.media_queries import MediaQueries
from .process_summary_command import ProcessSummaryCommand

# Import new SRP-compliant services
from ..services.summarization_metrics_service import SummarizationMetricsService
from ..services.summary_state_service import SummaryStateService
from ..services.summary_notification_service import SummaryNotificationService
from ..services.summarization_service import SummarizationService

logger = structlog.get_logger(__name__)


class ProcessSummaryCommandHandler:
    """
    Orchestrates the summarization process by coordinating with specialized services.
    """
    def __init__(
        self,
        state_service: SummaryStateService,
        notification_service: SummaryNotificationService,
        summarization_service: SummarizationService,
        metrics_service: SummarizationMetricsService,
        analytics_queries: AnalyticsQueries,
        event_bus: EventBus,
        media_queries: MediaQueries,
    ):
        self.state_service = state_service
        self.notification_service = notification_service
        self.summarization_service = summarization_service
        self.metrics_service = metrics_service
        self.analytics_queries = analytics_queries
        self.event_bus = event_bus
        self.media_queries = media_queries

    async def handle(self, command: ProcessSummaryCommand):
        start_time = time.time()
        logger.info("summarization.started", media_id=command.media_id, provider=command.provider)

        media = await self.media_queries.get_by_id(command.media_id)
        if not media:
            raise ValueError(f"Media with id {command.media_id} not found.")
        
        user_id = str(media.user_id)
        
        # 1. Start processing and get initial summary state
        summary = await self.state_service.start_processing(command.media_id, command.provider)
        await self.notification_service.push_update("summary", summary, user_id)

        try:
            # 2. Perform summarization
            summary_text = await self.summarization_service.summarize(command.text_content)

            # 3. Complete processing
            summary = await self.state_service.complete_processing(summary, summary_text)
            await self.notification_service.push_update("summary", summary, user_id)

            # 4. Record metrics
            duration = time.time() - start_time
            self.metrics_service.record_summarization_success(
                media_id=command.media_id, duration=duration, provider=command.provider
            )
            logger.info("summarization.completed", media_id=command.media_id, duration=duration)
            
            return summary

        except Exception as e:
            # 4a. Record failure metrics
            self.metrics_service.record_summarization_failure()
            logger.error("summarization.failed", media_id=command.media_id, error=str(e))
            
            # 3a. Set failure state
            summary = await self.state_service.fail_processing(summary, str(e))
            await self.notification_service.push_update("summary", summary, user_id)
            
            raise