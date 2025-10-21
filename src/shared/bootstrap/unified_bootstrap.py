"""
Unified bootstrap - eliminating bootstrap duplication
"""
from typing import Dict, Any, Type, TypeVar, Callable
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from src.shared.utils.simple_injection import container
from src.shared.domain.repository_base import IBaseRepository
from src.shared.infrastructure.unified_metrics import unified_metrics
from src.shared.infrastructure.unified_notification import UnifiedNotificationService

logger = structlog.get_logger(__name__)

T = TypeVar('T')

class UnifiedBootstrap:
    """Single bootstrap class for all modules - eliminating duplication"""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self._setup_core_services()
    
    def _setup_core_services(self):
        """Setup core shared services"""
        # Register core services in container
        container.register(UnifiedNotificationService, UnifiedNotificationService(None))  # Will be properly injected
        
    def bootstrap_module(
        self,
        module_name: str,
        repository_class: Type[IBaseRepository],
        entity_class: Type[T],
        additional_services: Dict[str, Callable] = None
    ) -> Dict[str, Any]:
        """Generic module bootstrap"""
        
        logger.info(f"Bootstrapping {module_name} module")
        
        # Create repository
        repository = repository_class(self.db_session)
        
        # Create queries service
        queries_class_name = f"{module_name.title()}Queries"
        
        # Base services every module needs
        services = {
            f"{module_name}_repository": repository,
            f"{module_name}_queries": self._create_queries_service(repository),
            "metrics_collector": unified_metrics,
        }
        
        # Add additional services if provided
        if additional_services:
            for service_name, service_factory in additional_services.items():
                try:
                    services[service_name] = service_factory()
                except Exception as e:
                    logger.warning(f"Failed to create service {service_name}: {e}")
        
        logger.info(f"Successfully bootstrapped {module_name} with {len(services)} services")
        return services
    
    def _create_queries_service(self, repository):
        """Create a generic queries service"""
        class GenericQueries:
            def __init__(self, repo):
                self.repository = repo
            
            async def get_by_id(self, entity_id):
                return await self.repository.find_by_id(entity_id)
            
            async def get_by_user_id(self, user_id, page=1, limit=10):
                return await self.repository.find_by_user_id(user_id, page, limit)
            
            async def exists(self, entity_id):
                return await self.repository.exists(entity_id)
        
        return GenericQueries(repository)
    
    def bootstrap_media_module(self, module_name: str, repository_class: Type) -> Dict[str, Any]:
        """Bootstrap for media-related modules (transcription, summary, etc.)"""
        
        def create_processor():
            """Create a generic processor service"""
            class GenericProcessor:
                def __init__(self):
                    self.metrics = unified_metrics
                
                async def process(self, command):
                    # Generic processing logic
                    operation_key = self.metrics.record_operation_start(
                        entity_type=module_name,
                        entity_id=str(getattr(command, 'id', 'unknown')),
                        operation='process'
                    )
                    
                    try:
                        # Actual processing would be implemented by specific modules
                        result = await self._do_process(command)
                        self.metrics.record_operation_success(operation_key, module_name)
                        return result
                    except Exception as e:
                        self.metrics.record_operation_failure(operation_key, module_name, str(e))
                        raise
                
                async def _do_process(self, command):
                    # Override in specific implementations
                    raise NotImplementedError("Specific processing logic not implemented")
            
            return GenericProcessor()
        
        additional_services = {
            f"{module_name}_processor": create_processor,
        }
        
        return self.bootstrap_module(
            module_name=module_name,
            repository_class=repository_class,
            entity_class=None,  # Will be inferred
            additional_services=additional_services
        )

# Global bootstrap instance
def create_unified_bootstrap(db_session: AsyncSession) -> UnifiedBootstrap:
    """Create unified bootstrap instance"""
    return UnifiedBootstrap(db_session)