# src/summarization/application/commands/process_summary_command_handler.py
import time
import structlog

from src.analytics.application.queries.analytics_queries import AnalyticsQueries
from src.metrics.application.metrics_service import MetricsService
from src.shared.events.domain_events import SummarizationProgress
from src.shared.events.event_bus import EventBus
from src.summarization.domain.interfaces import ISummaryRepository
from src.summarization.domain.summary import Summary, SummaryStatus
from src.summarization.infrastructure.interfaces import ISummarizer
from .process_summary_command import ProcessSummaryCommand
from src.shared.resilience.circuit_breaker import get_circuit_breaker

logger = structlog.get_logger(__name__)


class ProcessSummaryCommandHandler:
    def __init__(
        self,
        summarizer: ISummarizer,
        summary_repo: ISummaryRepository,
        metrics_service: MetricsService,
        analytics_queries: AnalyticsQueries,
        event_bus: EventBus,
    ):
        self.summarizer = summarizer
        self.summary_repo = summary_repo
        self.metrics_service = metrics_service
        self.analytics_queries = analytics_queries
        self.event_bus = event_bus

    async def handle(self, command: ProcessSummaryCommand) -> Summary:
        start_time = time.time()
        logger.info("summarization.started", media_id=command.media_id, provider=command.provider)

        summary = await self.summary_repo.find_by_media_id(command.media_id)
        if summary and summary.status == SummaryStatus.COMPLETED:
            logger.info("summarization.completed", media_id=command.media_id, from_cache=True)
            return summary

        if not summary:
            summary = Summary.create(media_id=command.media_id, provider=command.provider)
        else:
            summary.provider = command.provider
        
        await self.summary_repo.save(summary)

        try:
            if not command.text_content:
                raise ValueError("Text content is empty, cannot summarize.")

            # Pass the raw text length as the content metric
            text_length = len(command.text_content)
            estimate = await self.analytics_queries.estimate_processing_time(content_metric=float(text_length))

            await self.event_bus.publish(SummarizationProgress(
                media_id=command.media_id,
                progress=50,
                stage="summarization",
                estimated_total_seconds=estimate["estimated_total_seconds"]
            ))

            breaker_key = f"summarization_{self.summarizer.provider_name}"
            breaker = get_circuit_breaker(breaker_key)
            text = await breaker.call_async(self.summarizer.summarize, command.text_content)

            summary.mark_as_completed(text)

            duration = time.time() - start_time
            self.metrics_service.increment_summarization('success')
            self.metrics_service.observe_summarization_duration(
                media_id=command.media_id, 
                duration=duration, 
                provider=self.summarizer.provider_name
            )

            logger.info("summarization.completed", media_id=command.media_id, duration=duration)

            return await self.summary_repo.save(summary)

        except Exception as e:
            self.metrics_service.increment_summarization('failure')
            logger.error("summarization.failed", media_id=command.media_id, error=str(e))
            if summary:
                summary.mark_as_failed(str(e)[:500])
                await self.summary_repo.save(summary)
            raise
