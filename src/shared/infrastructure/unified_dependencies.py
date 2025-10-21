"""
Unified dependency injection - eliminating dependencies duplication
"""
from typing import Dict, Any, Callable, Optional, Type, TypeVar
from functools import lru_cache
import structlog

from src.shared.utils.simple_injection import container
from src.shared.config.unified_settings import get_settings
from src.shared.infrastructure.unified_metrics import unified_metrics
from src.shared.infrastructure.unified_notification import UnifiedNotificationService
from src.shared.infrastructure.unified_storage import StorageFactory
from src.shared.application.unified_services import ServiceFactory

logger = structlog.get_logger(__name__)

T = TypeVar('T')

class UnifiedDependencyProvider:
    """Single dependency provider for all modules"""
    
    def __init__(self):
        self.settings = get_settings()
        self._setup_core_dependencies()
    
    def _setup_core_dependencies(self):
        """Setup core shared dependencies"""
        try:
            # Register core services
            container.register(UnifiedNotificationService, self._create_notification_service())
            container.register(type(unified_metrics), unified_metrics)
            
            # Register storage factory
            storage_factory = StorageFactory()
            container.register(StorageFactory, storage_factory)
            
            logger.info("Core dependencies registered successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup core dependencies: {e}")
            raise
    
    def _create_notification_service(self) -> UnifiedNotificationService:
        """Create notification service instance"""
        # In a real implementation, this would inject the connection manager
        return UnifiedNotificationService(None)
    
    @lru_cache(maxsize=None)
    def get_validator(self, entity_type: str):
        """Get validator for entity type"""
        return ServiceFactory.create_validator(entity_type)
    
    @lru_cache(maxsize=None)
    def get_state_manager(self, entity_type: str):
        """Get state manager for entity type"""
        return ServiceFactory.create_state_manager(entity_type)
    
    @lru_cache(maxsize=None)
    def get_orchestrator(self, entity_type: str):
        """Get orchestrator for entity type"""
        return ServiceFactory.create_orchestrator(entity_type)
    
    def get_storage_service(self, provider: Optional[str] = None):
        """Get storage service instance"""
        provider = provider or self.settings.storage.provider
        storage_factory = container.get(StorageFactory)
        
        config = {
            "root_path": self.settings.storage.root_path,
            "bucket_name": self.settings.storage.bucket_name,
            "access_key": self.settings.storage.access_key,
            "secret_key": self.settings.storage.secret_key,
            "endpoint_url": self.settings.storage.endpoint_url
        }
        
        return storage_factory.create_storage(provider, **config)
    
    def get_repository(self, entity_type: str, db_session):
        """Get repository instance for entity type"""
        # Dynamic repository creation based on entity type
        repository_map = {
            "transcription": "src.transcription.infrastructure.transcription_repository.TranscriptionRepository",
            "summarization": "src.summarization.infrastructure.summary_repository.SummaryRepository", 
            "topic_modeling": "src.topic_modeling.infrastructure.topic_modeling_repository.TopicModelingRepository",
            "media": "src.media_management.infrastructure.media_repository.MediaRepository",
            "user": "src.auth.infrastructure.user_repository.UserRepository"
        }
        
        if entity_type not in repository_map:
            raise ValueError(f"Unknown entity type: {entity_type}")
        
        # Import and instantiate repository dynamically
        module_path, class_name = repository_map[entity_type].rsplit(".", 1)
        
        try:
            import importlib
            module = importlib.import_module(module_path)
            repository_class = getattr(module, class_name)
            return repository_class(db_session)
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to create repository for {entity_type}: {e}")
            raise
    
    def get_module_config(self, entity_type: str) -> Dict[str, Any]:
        """Get configuration for specific module"""
        return self.settings.get_module_config(entity_type)

# Global dependency provider
dependency_provider = UnifiedDependencyProvider()

# Convenience functions for FastAPI dependencies
def get_dependency_provider() -> UnifiedDependencyProvider:
    """Get dependency provider instance"""
    return dependency_provider

def get_validator_dependency(entity_type: str):
    """Create validator dependency function"""
    def _get_validator():
        return dependency_provider.get_validator(entity_type)
    return _get_validator

def get_state_manager_dependency(entity_type: str):
    """Create state manager dependency function"""
    def _get_state_manager():
        return dependency_provider.get_state_manager(entity_type)
    return _get_state_manager

def get_orchestrator_dependency(entity_type: str):
    """Create orchestrator dependency function"""
    def _get_orchestrator():
        return dependency_provider.get_orchestrator(entity_type)
    return _get_orchestrator

def get_storage_service_dependency(provider: Optional[str] = None):
    """Create storage service dependency function"""
    def _get_storage_service():
        return dependency_provider.get_storage_service(provider)
    return _get_storage_service

def get_metrics_dependency():
    """Get metrics collector dependency"""
    return unified_metrics

def get_notification_service_dependency():
    """Get notification service dependency"""
    return container.get(UnifiedNotificationService)

# Module-specific convenience functions
def get_transcription_dependencies():
    """Get all transcription dependencies"""
    return {
        "validator": dependency_provider.get_validator("transcription"),
        "state_manager": dependency_provider.get_state_manager("transcription"),
        "orchestrator": dependency_provider.get_orchestrator("transcription"),
        "metrics": unified_metrics,
        "config": dependency_provider.get_module_config("transcription")
    }

def get_summarization_dependencies():
    """Get all summarization dependencies"""
    return {
        "validator": dependency_provider.get_validator("summarization"),
        "state_manager": dependency_provider.get_state_manager("summarization"),
        "orchestrator": dependency_provider.get_orchestrator("summarization"),
        "metrics": unified_metrics,
        "config": dependency_provider.get_module_config("summarization")
    }

def get_topic_modeling_dependencies():
    """Get all topic modeling dependencies"""
    return {
        "validator": dependency_provider.get_validator("topic_modeling"),
        "state_manager": dependency_provider.get_state_manager("topic_modeling"),
        "orchestrator": dependency_provider.get_orchestrator("topic_modeling"),
        "metrics": unified_metrics,
        "config": dependency_provider.get_module_config("topic_modeling")
    }