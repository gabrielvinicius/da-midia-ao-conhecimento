# src/topic_modeling/__init__.py
"""
Topic modeling module following SOLID principles.

This module provides a clean, extensible topic modeling abstraction that follows:
- SRP: Each class has a single responsibility
- OCP: Easy to extend with new providers without modification
- LSP: All providers implement the same interface contract
- ISP: Segregated interfaces for different concerns
- DIP: High-level modules depend on abstractions

Usage:
    from src.topic_modeling import get_topic_modeling_orchestrator
    
    # Get orchestrator (auto-configured from environment)
    orchestrator = get_topic_modeling_orchestrator(session)
    
    # Process topic modeling
    result = await orchestrator.process_topic_modeling(
        media_id="123",
        text_content="Long text for topic extraction...",
        language="en",
        provider="sklearn_lda",
        user_id="user123",
        num_topics=5
    )
    
    # Get existing result
    existing = await orchestrator.get_topics("123")
    
    # Analyze text quality
    quality = await orchestrator.analyze_text_quality(text_content)
"""

# Domain exports
from src.topic_modeling.domain.topic_modeling import TopicModelingResult
from src.topic_modeling.domain.interfaces import (
    ITopicModelingRepository,
    TopicModelingProvider,
    TopicModelingProviderFactory,
    TopicModelingConfiguration,
    TopicModelingOrchestrator,
    TextPreprocessor,
    TopicValidator
)

# Application exports
from src.topic_modeling.application.commands.extract_topics_command import ExtractTopicsCommand
from src.topic_modeling.application.commands.extract_topics_command_handler import ExtractTopicsCommandHandler
from src.topic_modeling.application.queries.topic_modeling_queries import TopicModelingQueries
from src.topic_modeling.application.services.text_preprocessor import DefaultTextPreprocessor
from src.topic_modeling.application.services.topic_validator import DefaultTopicValidator

# Infrastructure exports
from src.topic_modeling.infrastructure.dependencies import (
    get_topic_modeling_orchestrator,
    get_topic_modeling_factory_dep,
    get_topic_modeling_logger_dep,
    get_topic_modeling_metrics_dep,
    get_text_preprocessor_dep,
    get_topic_validator_dep
)
from src.topic_modeling.infrastructure.factory import register_topic_modeling_provider

# Provider implementations
from src.topic_modeling.infrastructure.providers.sklearn_provider import (
    SklearnTopicModelingProvider, 
    SklearnConfiguration
)

# Try to import Gensim providers if available
try:
    from src.topic_modeling.infrastructure.providers.gensim_provider import (
        GensimTopicModelingProvider, 
        GensimConfiguration
    )
    GENSIM_AVAILABLE = True
except ImportError:
    GENSIM_AVAILABLE = False

__all__ = [
    # Domain
    "TopicModelingResult",
    "ITopicModelingRepository",
    "TopicModelingProvider",
    "TopicModelingProviderFactory",
    "TopicModelingConfiguration",
    "TopicModelingOrchestrator",
    "TextPreprocessor",
    "TopicValidator",
    
    # Application
    "ExtractTopicsCommand",
    "ExtractTopicsCommandHandler",
    "TopicModelingQueries",
    "DefaultTextPreprocessor",
    "DefaultTopicValidator",
    
    # Infrastructure
    "get_topic_modeling_orchestrator",
    "get_topic_modeling_factory_dep",
    "get_topic_modeling_logger_dep",
    "get_topic_modeling_metrics_dep",
    "get_text_preprocessor_dep",
    "get_topic_validator_dep",
    "register_topic_modeling_provider",
    
    # Providers
    "SklearnTopicModelingProvider",
    "SklearnConfiguration",
]

# Add Gensim exports if available
if GENSIM_AVAILABLE:
    __all__.extend([
        "GensimTopicModelingProvider",
        "GensimConfiguration",
    ])