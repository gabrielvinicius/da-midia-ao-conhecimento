# src/shared/bootstrap.py
"""
Bootstrap for shared module following SOLID principles.
Constructs and returns shared services used across the application.
"""
from typing import Dict, Any

# Infrastructure & Config
from src.shared.infrastructure.cache import CacheService
from src.shared.infrastructure.database import get_database_session
from src.shared.config.database_settings import DatabaseSettings
from src.shared.config.broker_settings import BrokerSettings

# Event System
from src.shared.events.event_bus import EventBus
from src.shared.events.event_publisher import EventPublisher
from src.shared.events.subscription_manager import SubscriptionManager

# Utility Services
from src.shared.application.services.file_service import FileService
from src.shared.application.services.id_service import IdService
from src.shared.application.services.password_service import PasswordService
from src.shared.application.services.validation_service import ValidationService

# Monitoring & Resilience
from src.shared.monitoring.metrics_collector import MetricsCollector
from src.shared.resilience.circuit_breaker import CircuitBreaker

# Middleware
from src.shared.middleware.performance_middleware import PerformanceMiddleware
from src.shared.middleware.validation_middleware import ValidationMiddleware


def bootstrap_shared_module() -> Dict[str, Any]:
    """Constructs and returns shared services following SOLID principles."""
    
    # --- Configuration Services ---
    database_settings = DatabaseSettings()
    broker_settings = BrokerSettings()
    
    # --- Infrastructure Services ---
    cache_service = CacheService()
    
    # --- Event System Services ---
    subscription_manager = SubscriptionManager()
    event_publisher = EventPublisher()
    event_bus = EventBus(
        publisher=event_publisher,
        subscription_manager=subscription_manager
    )
    
    # --- Utility Services ---
    file_service = FileService()
    id_service = IdService()
    password_service = PasswordService()
    validation_service = ValidationService()
    
    # --- Monitoring & Resilience Services ---
    metrics_collector = MetricsCollector()
    circuit_breaker = CircuitBreaker()
    
    # --- Middleware Services ---
    performance_middleware = PerformanceMiddleware(metrics_collector=metrics_collector)
    validation_middleware = ValidationMiddleware(validation_service=validation_service)
    
    return {
        # Configuration
        "database_settings": database_settings,
        "broker_settings": broker_settings,
        
        # Infrastructure
        "cache_service": cache_service,
        
        # Events
        "event_bus": event_bus,
        "event_publisher": event_publisher,
        "subscription_manager": subscription_manager,
        
        # Utilities
        "file_service": file_service,
        "id_service": id_service,
        "password_service": password_service,
        "validation_service": validation_service,
        
        # Monitoring & Resilience
        "metrics_collector": metrics_collector,
        "circuit_breaker": circuit_breaker,
        
        # Middleware
        "performance_middleware": performance_middleware,
        "validation_middleware": validation_middleware,
    }