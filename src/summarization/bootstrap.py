# src/summarization/bootstrap.py
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from src.shared.events.event_bus import EventBus
from src.metrics.domain.metrics import MetricsProvider
from src.summarization.application.commands.request_summary_command_handler import RequestSummaryCommandHandler
from src.summarization.application.queries.summary_queries import SummaryQueries
from src.summarization.application.services.summarization_metrics_service import SummarizationMetricsService
from src.summarization.infrastructure.summary_repository import SummaryRepository

def bootstrap_summarization_module(
    db_session: AsyncSession,
    event_bus: EventBus,
    metrics_provider: MetricsProvider,
) -> Dict[str, Any]:
    """Constructs and returns the services for the summarization module."""
    summary_repository = SummaryRepository(session=db_session)
    summary_queries = SummaryQueries(summary_repository=summary_repository)
    request_summary_command_handler = RequestSummaryCommandHandler(event_bus=event_bus)
    summarization_metrics_service = SummarizationMetricsService(metrics_provider=metrics_provider)

    return {
        "summary_repository": summary_repository,
        "summary_queries": summary_queries,
        "request_summary_command_handler": request_summary_command_handler,
        "summarization_metrics_service": summarization_metrics_service,
    }
