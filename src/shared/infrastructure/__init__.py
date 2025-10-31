"""Public exports for the shared infrastructure package.

The former "unified" facade (bootstrap, metrics, notification, storage) was
removed in favour of concrete services that are maintained elsewhere in the
codebase.  Only the actively used building blocks that do not rely on optional
runtime dependencies are re-exported here so that callers can keep importing
the production-ready helpers directly from this package.
"""

from .database import (
    AsyncSessionLocal,
    Base,
    SessionLocal,
    engine,
    engine_sync,
    get_db,
    get_db_session,
    get_session,
    get_sync_db,
)
from .logging_config import configure_logging, get_logger
from .tracing import configure_tracer
from .unified_providers import (
    ProviderFactory,
    ProviderRegistry,
    ProviderResult,
    ProviderType,
    SummarizationProvider,
    TopicModelingProvider,
    TranscriptionProvider,
    provider_registry,
)

__all__ = [
    "AsyncSessionLocal",
    "Base",
    "SessionLocal",
    "engine",
    "engine_sync",
    "get_db",
    "get_db_session",
    "get_session",
    "get_sync_db",
    "configure_logging",
    "get_logger",
    "configure_tracer",
    "ProviderFactory",
    "ProviderRegistry",
    "ProviderResult",
    "ProviderType",
    "SummarizationProvider",
    "TopicModelingProvider",
    "TranscriptionProvider",
    "provider_registry",
]
