# src/summarization/__init__.py
"""
Summarization module following SOLID principles.

This module provides a clean, extensible summarization abstraction that follows:
- SRP: Each class has a single responsibility
- OCP: Easy to extend with new providers without modification
- LSP: All providers implement the same interface contract
- ISP: Segregated interfaces for different concerns
- DIP: High-level modules depend on abstractions

Usage:
    from src.summarization import get_summary_orchestrator
    
    # Get orchestrator (auto-configured from environment)
    orchestrator = get_summary_orchestrator(session)
    
    # Process summarization
    summary = await orchestrator.process_summarization(
        media_id="123",
        text_content="Long text to summarize...",
        provider="huggingface",
        user_id="user123"
    )
    
    # Get existing summary
    existing = await orchestrator.get_summary("123")
"""

# Domain exports
from src.summarization.domain.summary import Summary, SummaryStatus
from src.summarization.domain.interfaces import (
    ISummaryRepository,
    SummaryProvider,
    SummaryProviderFactory,
    SummaryConfiguration,
    SummaryOrchestrator
)

# Application exports
from src.summarization.application.commands.process_summary_command import ProcessSummaryCommand
from src.summarization.application.commands.process_summary_command_handler import ProcessSummaryCommandHandler
from src.summarization.application.commands.request_summary_command import RequestSummaryCommand
from src.summarization.application.commands.request_summary_command_handler import RequestSummaryCommandHandler

# Infrastructure exports
from src.summarization.infrastructure.dependencies import (
    get_summary_orchestrator,
    get_summary_factory_dep,
    get_summary_logger_dep,
    get_summary_metrics_dep
)
from src.summarization.infrastructure.factory import register_summary_provider

# Provider implementations
from src.summarization.infrastructure.providers.huggingface_provider import (
    HuggingFaceSummaryProvider, 
    HuggingFaceConfiguration
)
from src.summarization.infrastructure.providers.openai_provider import (
    OpenAISummaryProvider, 
    OpenAIConfiguration
)

__all__ = [
    # Domain
    "Summary",
    "SummaryStatus",
    "ISummaryRepository",
    "SummaryProvider",
    "SummaryProviderFactory",
    "SummaryConfiguration",
    "SummaryOrchestrator",
    
    # Application
    "ProcessSummaryCommand",
    "ProcessSummaryCommandHandler",
    "RequestSummaryCommand",
    "RequestSummaryCommandHandler",
    
    # Infrastructure
    "get_summary_orchestrator",
    "get_summary_factory_dep",
    "get_summary_logger_dep",
    "get_summary_metrics_dep",
    "register_summary_provider",
    
    # Providers
    "HuggingFaceSummaryProvider",
    "HuggingFaceConfiguration",
    "OpenAISummaryProvider",
    "OpenAIConfiguration",
]