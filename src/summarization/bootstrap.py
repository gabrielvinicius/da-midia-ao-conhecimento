# src/summarization/bootstrap.py
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from src.shared.events.event_bus import EventBus
from src.shared.infrastructure.cache import CacheService
from src.shared.monitoring.metrics_collector import MetricsCollector
from src.summarization.application.commands.request_summary_command_handler import RequestSummaryCommandHandler
from src.summarization.application.queries.summary_queries import SummaryQueries

# Enhanced SOLID services
from src.summarization.application.services.summarization_service import SummarizationService
from src.summarization.application.services.summary_validator import SummaryValidator
from src.summarization.application.services.summary_metrics_service import SummaryMetricsService
from src.summarization.application.services.summary_state_manager_impl import SummaryStateManagerImpl
from src.summarization.infrastructure.summary_repository import SummaryRepository
from src.summarization.infrastructure.interfaces import ISummarizer

def bootstrap_summarization_module(
    db_session: AsyncSession,
    event_bus: EventBus,
    metrics_collector: MetricsCollector,
    cache_service: CacheService,
    summarizer_provider: ISummarizer,
) -> Dict[str, Any]:
    """Constructs and returns the SOLID-enhanced services for the summarization module."""
    
    # --- Infrastructure ---
    summary_repository = SummaryRepository(session=db_session)
    summary_queries = SummaryQueries(summary_repository=summary_repository)
    
    # --- SOLID Services (Following SRP) ---
    summary_validator = SummaryValidator(
        min_text_length=100,
        max_text_length=50000
    )
    
    summary_metrics_service = SummaryMetricsService(
        metrics_collector=metrics_collector
    )
    
    summary_state_manager = SummaryStateManagerImpl(
        cache_service=cache_service
    )
    
    # --- Enhanced Summarization Service (Following all SOLID principles) ---
    summarization_service = SummarizationService(
        summarizer_provider=summarizer_provider,
        validator=summary_validator,
        metrics_service=summary_metrics_service,
        state_manager=summary_state_manager
    )
    
    # --- Command Handlers ---
    request_summary_command_handler = RequestSummaryCommandHandler(
        event_bus=event_bus
    )

    return {
        # Infrastructure
        "summary_repository": summary_repository,
        "summary_queries": summary_queries,
        
        # SOLID Services
        "summary_validator": summary_validator,
        "summary_metrics_service": summary_metrics_service,
        "summary_state_manager": summary_state_manager,
        "summarization_service": summarization_service,
        
        # Command Handlers
        "request_summary_command_handler": request_summary_command_handler,
        
        # Legacy compatibility
        "summarization_metrics_service": summary_metrics_service,  # For backward compatibility
    }
