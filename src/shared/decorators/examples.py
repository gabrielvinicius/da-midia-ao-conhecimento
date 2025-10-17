"""
Examples of applying Decorator Pattern to existing services
"""
from uuid import UUID
from typing import Optional, List, Dict, Any
from .decorator_factory import read_operation, write_operation, processing_operation, service_operation


# Example 1: Media Management Service with decorators
class EnhancedMediaService:
    """Example of media service with applied decorators"""
    
    @read_operation("media_management", "get_media_by_id")
    async def get_media_by_id(self, media_id: UUID) -> Optional[Dict[str, Any]]:
        """Get media by ID with caching and retry"""
        # Simulated service logic
        # This will automatically have:
        # - Input validation (UUID validation)
        # - Caching (5min TTL with smart extension)
        # - Retry on failures (2 attempts with 0.5s delay)
        # - Performance metrics
        # - Operation logging
        pass
    
    @read_operation("media_management", "get_user_media")
    async def get_user_media(self, user_id: UUID, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user media with optimized read decorators"""
        # Cached, validated, monitored, logged
        pass
    
    @write_operation("media_management", "create_media")
    async def create_media(
        self, 
        user_id: UUID, 
        title: str, 
        file_data: bytes, 
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create media with comprehensive write decorators"""
        # This will automatically have:
        # - Strict input/output validation
        # - No caching (write operation)
        # - Retry with circuit breaker (3 attempts)
        # - Performance monitoring with lower threshold
        # - Detailed operation logging with args/results
        pass
    
    @write_operation("media_management", "update_media")
    async def update_media(self, media_id: UUID, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update media with write protection"""
        pass
    
    @write_operation("media_management", "delete_media")
    async def delete_media(self, media_id: UUID, user_id: UUID) -> bool:
        """Delete media with audit trail"""
        pass


# Example 2: Transcription Service with processing decorators
class EnhancedTranscriptionService:
    """Example of transcription service with processing decorators"""
    
    @processing_operation("transcription", "process_audio_transcription")
    async def process_audio_transcription(
        self,
        audio_data: bytes,
        language: str = "en",
        provider: str = "whisper"
    ) -> Dict[str, Any]:
        """Process audio transcription with resilient decorators"""
        # This will automatically have:
        # - Input validation (bytes validation, language validation)
        # - No caching (processing operations are unique)
        # - Retry with circuit breaker (2 attempts, higher delays)
        # - Performance monitoring (5 second threshold)
        # - Detailed operation logging
        pass
    
    @processing_operation("transcription", "process_video_transcription")
    async def process_video_transcription(
        self,
        video_data: bytes,
        extract_audio: bool = True,
        language: str = "auto"
    ) -> Dict[str, Any]:
        """Process video transcription with full monitoring"""
        pass


# Example 3: Custom decorator configuration
class EnhancedSummarizationService:
    """Example with custom decorator configuration"""
    
    @service_operation(
        "generic",
        "summarization", 
        "generate_summary",
        validation=True,
        validation_config={
            'validate_inputs': True,
            'validate_outputs': True,
            'strict_typing': True
        },
        cache=True,
        cache_config={
            'smart_cache': True,
            'ttl_seconds': 600,  # 10 minutes for summaries
            'max_ttl_seconds': 7200  # Max 2 hours
        },
        retry=True,
        retry_config={
            'max_attempts': 3,
            'base_delay': 2.0,
            'circuit_breaker': True,
            'failure_threshold': 2
        },
        metrics=True,
        metrics_config={
            'performance_monitoring': True,
            'threshold_ms': 10000.0,  # 10 seconds for AI operations
            'collect_args': True,
            'collect_results': True
        },
        logging=True,
        logging_config={
            'operation_logging': True,
            'include_args': True,
            'include_result': False  # Don't log large summary results
        }
    )
    async def generate_summary(
        self,
        text: str,
        max_length: int = 150,
        provider: str = "openai"
    ) -> Dict[str, Any]:
        """Generate text summary with custom decorator configuration"""
        pass


# Example 4: Applying decorators to existing service classes
def enhance_existing_service(service_class):
    """Function to apply decorators to existing service classes"""
    
    # Apply read decorators to query methods
    read_methods = [
        'get_by_id', 'find_by_id', 'get_all', 'search', 'exists',
        'list_', 'fetch_', 'retrieve_', 'query_'
    ]
    
    for method_name in dir(service_class):
        method = getattr(service_class, method_name)
        if callable(method) and not method_name.startswith('_'):
            
            # Determine operation type by method name
            if any(pattern in method_name for pattern in read_methods):
                # Apply read operation decorator
                decorated_method = read_operation()(method)
                setattr(service_class, method_name, decorated_method)
            
            elif any(pattern in method_name for pattern in ['create', 'save', 'update', 'delete']):
                # Apply write operation decorator
                decorated_method = write_operation()(method)
                setattr(service_class, method_name, decorated_method)
            
            elif any(pattern in method_name for pattern in ['process', 'analyze', 'transform', 'generate']):
                # Apply processing operation decorator
                decorated_method = processing_operation()(method)
                setattr(service_class, method_name, decorated_method)
    
    return service_class


# Example 5: Business rule validation decorator
from .validation_decorator import BusinessValidationDecorator

def business_rules_validation(**business_rules):
    """Custom decorator for business rule validation"""
    def decorator_wrapper(func):
        validator = BusinessValidationDecorator(business_rules)
        return validator.decorate(func)
    return decorator_wrapper


class EnhancedUserService:
    """Example with business rule validation"""
    
    @business_rules_validation(
        user_age_check=lambda *args, **kwargs: kwargs.get('age', 0) >= 18,
        valid_email=lambda *args, **kwargs: '@' in kwargs.get('email', ''),
        unique_username=lambda *args, **kwargs: len(kwargs.get('username', '')) >= 3
    )
    @write_operation("auth", "create_user")
    async def create_user(
        self,
        username: str,
        email: str,
        password: str,
        age: int
    ) -> Dict[str, Any]:
        """Create user with business rule validation"""
        pass


# Example 6: Monitoring and debugging utilities
class DecoratorMonitoring:
    """Utilities for monitoring decorator performance"""
    
    @staticmethod
    def get_metrics_report(module_name: str = None) -> Dict[str, Any]:
        """Get comprehensive metrics report"""
        from .metrics_decorator import MetricsCollector
        from .cache_decorator import CacheManager
        
        collector = MetricsCollector()
        cache_manager = CacheManager()
        
        return {
            "performance_metrics": collector.get_metrics_summary(module_name),
            "cache_statistics": cache_manager.get_stats(),
            "cache_cleanup_results": cache_manager.cleanup_expired()
        }
    
    @staticmethod
    def reset_all_metrics():
        """Reset all decorator metrics for fresh start"""
        from .metrics_decorator import MetricsCollector
        from .cache_decorator import CacheManager
        
        MetricsCollector().reset_metrics()
        CacheManager().clear()


# Example usage in actual service files:
"""
# In src/media_management/application/services/media_service.py
from src.shared.decorators.decorator_factory import read_operation, write_operation

class MediaService:
    
    @read_operation("media_management", "get_media_by_id")
    async def get_media_by_id(self, media_id: UUID) -> Optional[Media]:
        # Existing implementation with automatic decorators
        pass
    
    @write_operation("media_management", "create_media")
    async def create_media(self, user_id: UUID, media_data: Dict) -> Media:
        # Existing implementation with automatic decorators
        pass
"""