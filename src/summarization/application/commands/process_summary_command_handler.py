# src/summarization/application/commands/process_summary_command_handler.py
import time
import json
import structlog
from pydantic import BaseModel

from src.analytics.application.queries.analytics_queries import AnalyticsQueries
from src.metrics.application.metrics_service import MetricsService
from src.shared.events.domain_events import SummarizationProgress
from src.shared.events.event_bus import EventBus
from src.summarization.domain.interfaces import ISummaryRepository
from src.summarization.domain.summary import Summary
from src.summarization.infrastructure.interfaces import ISummarizer
from src.media_management.application.queries.media_queries import MediaQueries
from src.notifications.infrastructure.connection_manager import ConnectionManager
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
        media_queries: MediaQueries, # Added dependency
        connection_manager: ConnectionManager, # Added dependency
    ):
        self.summarizer = summarizer
        self.summary_repo = summary_repo
        self.metrics_service = metrics_service
        self.analytics_queries = analytics_queries
        self.event_bus = event_bus
        self.media_queries = media_queries
        self.connection_manager = connection_manager

    async def _push_update(self, entity_name: str, entity: BaseModel, user_id: str):
        """Helper method to push entity updates via WebSocket."""
        message = {
            "type": "entity_update",
            "entity": entity_name,
            "payload": json.loads(entity.model_dump_json())
        }
        await self.connection_manager.send_personal_message(json.dumps(message), user_id)
        logger.info(f"{entity_name}.pushed_realtime_update", id=str(entity.id), user_id=user_id)

    async def handle(self, command: ProcessSummaryCommand) -> Summary:
        start_time = time.time()
        logger.info("summarization.started", media_id=command.media_id, provider=command.provider)

        media = await self.media_queries.get_by_id(command.media_id)
        if not media:
            raise ValueError(f"Media with id {command.media_id} not found.")
        
        user_id = str(media.user_id)
        summary = await self.summary_repo.find_by_media_id(command.media_id)

        if summary and summary.text:
            logger.info("summarization.completed", media_id=command.media_id, from_cache=True)
            return summary

        if not summary:
            summary = Summary.create(media_id=command.media_id, provider=command.provider)
        else:
            summary.provider = command.provider
        
        summary.process()
        await self.summary_repo.save(summary)
        await self._push_update("summary", summary, user_id)

        try:
            if not command.text_content:
                raise ValueError("Text content is empty, cannot summarize.")

            text_length = len(command.text_content)
            estimate = await self.analytics_queries.estimate_processing_time(content_metric=float(text_length))

            await self.event_bus.publish(SummarizationProgress(
                media_id=command.media_id, progress=50, stage="summarization", estimated_total_seconds=estimate["estimated_total_seconds"]
            ))

            breaker = get_circuit_breaker(f"summarization_{self.summarizer.provider_name}")
            text = await breaker.call_async(self.summarizer.summarize, command.text_content)

            summary.mark_as_completed(text)
            saved_summary = await self.summary_repo.save(summary)
            await self._push_update("summary", saved_summary, user_id)

            duration = time.time() - start_time
            self.metrics_service.increment_summarization('success')
            self.metrics_service.observe_summarization_duration(media_id=command.media_id, duration=duration, provider=self.summarizer.provider_name)

            logger.info("summarization.completed", media_id=command.media_id, duration=duration)
            return saved_summary

        except Exception as e:
            self.metrics_service.increment_summarization('failure')
            logger.error("summarization.failed", media_id=command.media_id, error=str(e))
            if summary:
                summary.mark_as_failed(str(e)[:500])
                await self.summary_repo.save(summary)
                await self._push_update("summary", summary, user_id)
            raise
