# src/summarization/infrastructure/dependencies.py
"""
Dependency injection setup for summarization module - DIP compliance.
"""
import os
from typing import Optional

from src.summarization.domain.interfaces import (
    ISummaryRepository,
    SummaryProviderFactory,
    SummaryOperationLogger,
    SummaryMetrics,
    SummaryNotificationService,
    SummaryStateManager,
    SummaryOrchestrator
)
from src.summarization.domain.services.summary_coordinator import SummaryCoordinator
from src.summarization.application.services.summary_state_manager import SummaryStateManagerImpl
from src.summarization.application.services.summary_orchestrator import SummaryOrchestratorImpl
from src.summarization.infrastructure.factory import get_summary_factory
from src.summarization.infrastructure.logging import StructuredSummaryLogger, NoOpSummaryLogger
from src.summarization.infrastructure.metrics import PrometheusSummaryMetrics, NoOpSummaryMetrics
from src.summarization.infrastructure.notification_service import (
    WebSocketSummaryNotificationService, 
    NoOpSummaryNotificationService
)
from src.summarization.infrastructure.providers.huggingface_provider import HuggingFaceConfiguration
from src.summarization.infrastructure.providers.openai_provider import OpenAIConfiguration
from src.summarization.infrastructure.summary_repository import SummaryRepository


class SummarizationDependencyContainer:
    """
    Dependency injection container for summarization module.
    Follows DIP by managing dependencies through abstractions.
    """
    
    def __init__(self):
        self._factory: Optional[SummaryProviderFactory] = None
        self._logger: Optional[SummaryOperationLogger] = None
        self._metrics: Optional[SummaryMetrics] = None
        self._notification_service: Optional[SummaryNotificationService] = None
        self._state_manager: Optional[SummaryStateManager] = None
        self._orchestrator: Optional[SummaryOrchestrator] = None
    
    def get_summary_factory(self) -> SummaryProviderFactory:
        """Get summarization provider factory."""
        if self._factory is None:
            self._factory = get_summary_factory()
        return self._factory
    
    def get_summary_logger(self) -> SummaryOperationLogger:
        """Get summarization operation logger."""
        if self._logger is None:
            if os.getenv("ENABLE_SUMMARIZATION_LOGGING", "true").lower() == "true":
                self._logger = StructuredSummaryLogger()
            else:
                self._logger = NoOpSummaryLogger()
        return self._logger
    
    def get_summary_metrics(self) -> SummaryMetrics:
        """Get summarization metrics collector."""
        if self._metrics is None:
            if os.getenv("ENABLE_SUMMARIZATION_METRICS", "true").lower() == "true":
                self._metrics = PrometheusSummaryMetrics()
            else:
                self._metrics = NoOpSummaryMetrics()
        return self._metrics
    
    def get_notification_service(self) -> SummaryNotificationService:
        """Get notification service."""
        if self._notification_service is None:
            # This would be injected from the notifications module
            # For now, use no-op for testing
            self._notification_service = NoOpSummaryNotificationService()
        return self._notification_service
    
    def get_state_manager(self, repository: ISummaryRepository) -> SummaryStateManager:
        """Get summary state manager."""
        if self._state_manager is None:
            self._state_manager = SummaryStateManagerImpl(repository)
        return self._state_manager
    
    def get_orchestrator(self, session) -> SummaryOrchestrator:
        """Get high-level summarization orchestrator."""
        if self._orchestrator is None:
            # Create repository
            repository = SummaryRepository(session)
            
            # Create provider
            provider_type = os.getenv("SUMMARIZATION_PROVIDER", "huggingface")
            provider = self._create_provider(provider_type)
            
            # Create coordinator
            coordinator = SummaryCoordinator(
                provider=provider,
                logger=self.get_summary_logger(),
                metrics=self.get_summary_metrics(),
                notification_service=self.get_notification_service()
            )
            
            # Create state manager
            state_manager = self.get_state_manager(repository)
            
            # Create orchestrator
            self._orchestrator = SummaryOrchestratorImpl(
                repository=repository,
                state_manager=state_manager,
                coordinator=coordinator
            )
        
        return self._orchestrator
    
    def _create_provider(self, provider_type: str):
        """Create summarization provider based on type."""
        factory = self.get_summary_factory()
        
        if provider_type == "huggingface":
            config = HuggingFaceConfiguration(
                model_name=os.getenv("HUGGINGFACE_MODEL", "google-t5/t5-base"),
                max_input_length=int(os.getenv("MAX_INPUT_LENGTH", "512")),
                max_output_length=int(os.getenv("MAX_OUTPUT_LENGTH", "64")),
                device=os.getenv("SUMMARIZATION_DEVICE", "auto")
            )
        elif provider_type == "openai":
            config = OpenAIConfiguration(
                api_key=os.getenv("OPENAI_API_KEY", ""),
                model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
                max_input_length=int(os.getenv("MAX_INPUT_LENGTH", "4000")),
                max_output_length=int(os.getenv("MAX_OUTPUT_LENGTH", "150")),
                temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.3"))
            )
        else:
            raise ValueError(f"Unknown summarization provider: {provider_type}")
        
        return factory.create_provider(provider_type, config)


# Global container instance
_container = SummarizationDependencyContainer()


def get_summary_orchestrator(session) -> SummaryOrchestrator:
    """Dependency provider for summarization orchestrator."""
    return _container.get_orchestrator(session)


def get_summary_factory_dep() -> SummaryProviderFactory:
    """Dependency provider for summarization factory."""
    return _container.get_summary_factory()


def get_summary_logger_dep() -> SummaryOperationLogger:
    """Dependency provider for summarization logger."""
    return _container.get_summary_logger()


def get_summary_metrics_dep() -> SummaryMetrics:
    """Dependency provider for summarization metrics."""
    return _container.get_summary_metrics()