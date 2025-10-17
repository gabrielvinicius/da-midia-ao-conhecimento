# src/topic_modeling/infrastructure/dependencies.py
"""
Dependency injection setup for topic modeling module - DIP compliance.
"""
import os
from typing import Optional

from src.topic_modeling.domain.interfaces import (
    ITopicModelingRepository,
    TopicModelingProviderFactory,
    TopicModelingOperationLogger,
    TopicModelingMetrics,
    TopicModelingNotificationService,
    TopicModelingStateManager,
    TopicModelingOrchestrator,
    TextPreprocessor,
    TopicValidator
)
from src.topic_modeling.domain.services.topic_modeling_coordinator import TopicModelingCoordinator
from src.topic_modeling.application.services.topic_modeling_state_manager import TopicModelingStateManagerImpl
from src.topic_modeling.application.services.topic_modeling_orchestrator import TopicModelingOrchestratorImpl
from src.topic_modeling.application.services.text_preprocessor import DefaultTextPreprocessor
from src.topic_modeling.application.services.topic_validator import DefaultTopicValidator
from src.topic_modeling.infrastructure.factory import get_topic_modeling_factory
from src.topic_modeling.infrastructure.logging import StructuredTopicModelingLogger, NoOpTopicModelingLogger
from src.topic_modeling.infrastructure.metrics import PrometheusTopicModelingMetrics, NoOpTopicModelingMetrics
from src.topic_modeling.infrastructure.notification_service import (
    WebSocketTopicModelingNotificationService, 
    NoOpTopicModelingNotificationService
)
from src.topic_modeling.infrastructure.providers.sklearn_provider import SklearnConfiguration
from src.topic_modeling.infrastructure.providers.gensim_provider import GensimConfiguration
from src.topic_modeling.infrastructure.topic_modeling_repository import TopicModelingRepository


class TopicModelingDependencyContainer:
    """
    Dependency injection container for topic modeling module.
    Follows DIP by managing dependencies through abstractions.
    """
    
    def __init__(self):
        self._factory: Optional[TopicModelingProviderFactory] = None
        self._logger: Optional[TopicModelingOperationLogger] = None
        self._metrics: Optional[TopicModelingMetrics] = None
        self._notification_service: Optional[TopicModelingNotificationService] = None
        self._preprocessor: Optional[TextPreprocessor] = None
        self._validator: Optional[TopicValidator] = None
        self._orchestrator: Optional[TopicModelingOrchestrator] = None
    
    def get_topic_modeling_factory(self) -> TopicModelingProviderFactory:
        """Get topic modeling provider factory."""
        if self._factory is None:
            self._factory = get_topic_modeling_factory()
        return self._factory
    
    def get_topic_modeling_logger(self) -> TopicModelingOperationLogger:
        """Get topic modeling operation logger."""
        if self._logger is None:
            if os.getenv("ENABLE_TOPIC_MODELING_LOGGING", "true").lower() == "true":
                self._logger = StructuredTopicModelingLogger()
            else:
                self._logger = NoOpTopicModelingLogger()
        return self._logger
    
    def get_topic_modeling_metrics(self) -> TopicModelingMetrics:
        """Get topic modeling metrics collector."""
        if self._metrics is None:
            if os.getenv("ENABLE_TOPIC_MODELING_METRICS", "true").lower() == "true":
                self._metrics = PrometheusTopicModelingMetrics()
            else:
                self._metrics = NoOpTopicModelingMetrics()
        return self._metrics
    
    def get_notification_service(self) -> TopicModelingNotificationService:
        """Get notification service."""
        if self._notification_service is None:
            # This would be injected from the notifications module
            # For now, use no-op for testing
            self._notification_service = NoOpTopicModelingNotificationService()
        return self._notification_service
    
    def get_text_preprocessor(self) -> TextPreprocessor:
        """Get text preprocessor."""
        if self._preprocessor is None:
            min_text_length = int(os.getenv("TOPIC_MIN_TEXT_LENGTH", "100"))
            max_text_length = int(os.getenv("TOPIC_MAX_TEXT_LENGTH", "100000"))
            min_word_count = int(os.getenv("TOPIC_MIN_WORD_COUNT", "50"))
            
            self._preprocessor = DefaultTextPreprocessor(
                min_text_length=min_text_length,
                max_text_length=max_text_length,
                min_word_count=min_word_count,
                remove_urls=os.getenv("TOPIC_REMOVE_URLS", "true").lower() == "true",
                remove_emails=os.getenv("TOPIC_REMOVE_EMAILS", "true").lower() == "true",
                normalize_whitespace=os.getenv("TOPIC_NORMALIZE_WHITESPACE", "true").lower() == "true"
            )
        return self._preprocessor
    
    def get_topic_validator(self) -> TopicValidator:
        """Get topic validator."""
        if self._validator is None:
            min_coherence_score = float(os.getenv("TOPIC_MIN_COHERENCE", "0.1"))
            min_words_per_topic = int(os.getenv("TOPIC_MIN_WORDS_PER_TOPIC", "3"))
            max_words_per_topic = int(os.getenv("TOPIC_MAX_WORDS_PER_TOPIC", "20"))
            
            self._validator = DefaultTopicValidator(
                min_coherence_score=min_coherence_score,
                min_words_per_topic=min_words_per_topic,
                max_words_per_topic=max_words_per_topic,
                min_topic_score=float(os.getenv("TOPIC_MIN_SCORE", "0.01")),
                diversity_threshold=float(os.getenv("TOPIC_DIVERSITY_THRESHOLD", "0.3"))
            )
        return self._validator
    
    def get_orchestrator(self, session) -> TopicModelingOrchestrator:
        """Get high-level topic modeling orchestrator."""
        if self._orchestrator is None:
            # Create repository
            repository = TopicModelingRepository(session)
            
            # Create provider
            provider_type = os.getenv("TOPIC_MODELING_PROVIDER", "sklearn_lda")
            provider = self._create_provider(provider_type)
            
            # Create coordinator
            coordinator = TopicModelingCoordinator(
                provider=provider,
                preprocessor=self.get_text_preprocessor(),
                validator=self.get_topic_validator(),
                logger=self.get_topic_modeling_logger(),
                metrics=self.get_topic_modeling_metrics(),
                notification_service=self.get_notification_service()
            )
            
            # Create state manager
            state_manager = TopicModelingStateManagerImpl(repository)
            
            # Create orchestrator
            self._orchestrator = TopicModelingOrchestratorImpl(
                repository=repository,
                state_manager=state_manager,
                coordinator=coordinator
            )
        
        return self._orchestrator
    
    def _create_provider(self, provider_type: str):
        """Create topic modeling provider based on type."""
        factory = self.get_topic_modeling_factory()
        
        if provider_type.startswith("sklearn_"):
            algorithm = provider_type.replace("sklearn_", "")
            config_params = {
                "algorithm": algorithm,
                "max_text_length": int(os.getenv("TOPIC_MAX_TEXT_LENGTH", "100000")),
                "max_features": int(os.getenv("SKLEARN_MAX_FEATURES", "1000")),
                "min_df": int(os.getenv("SKLEARN_MIN_DF", "2")),
                "max_df": float(os.getenv("SKLEARN_MAX_DF", "0.95")),
                "random_state": int(os.getenv("SKLEARN_RANDOM_STATE", "42"))
            }
        elif provider_type.startswith("gensim_"):
            algorithm = provider_type.replace("gensim_", "")
            config_params = {
                "algorithm": algorithm,
                "max_text_length": int(os.getenv("TOPIC_MAX_TEXT_LENGTH", "200000")),
                "min_word_count": int(os.getenv("GENSIM_MIN_WORD_COUNT", "5")),
                "no_below": int(os.getenv("GENSIM_NO_BELOW", "2")),
                "no_above": float(os.getenv("GENSIM_NO_ABOVE", "0.8")),
                "passes": int(os.getenv("GENSIM_PASSES", "10")),
                "iterations": int(os.getenv("GENSIM_ITERATIONS", "400")),
                "random_state": int(os.getenv("GENSIM_RANDOM_STATE", "42"))
            }
        else:
            raise ValueError(f"Unknown topic modeling provider: {provider_type}")
        
        return factory.create_provider_with_params(provider_type, **config_params)


# Global container instance
_container = TopicModelingDependencyContainer()


def get_topic_modeling_orchestrator(session) -> TopicModelingOrchestrator:
    """Dependency provider for topic modeling orchestrator."""
    return _container.get_orchestrator(session)


def get_topic_modeling_factory_dep() -> TopicModelingProviderFactory:
    """Dependency provider for topic modeling factory."""
    return _container.get_topic_modeling_factory()


def get_topic_modeling_logger_dep() -> TopicModelingOperationLogger:
    """Dependency provider for topic modeling logger."""
    return _container.get_topic_modeling_logger()


def get_topic_modeling_metrics_dep() -> TopicModelingMetrics:
    """Dependency provider for topic modeling metrics."""
    return _container.get_topic_modeling_metrics()


def get_text_preprocessor_dep() -> TextPreprocessor:
    """Dependency provider for text preprocessor."""
    return _container.get_text_preprocessor()


def get_topic_validator_dep() -> TopicValidator:
    """Dependency provider for topic validator."""
    return _container.get_topic_validator()