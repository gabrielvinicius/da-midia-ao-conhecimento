"""
Decorator Factory for easy decorator composition and application
"""
from typing import Any, Callable, Dict, List, Optional
from .base_decorator import IServiceDecorator, CompositeDecorator
from .logging_decorator import LoggingDecorator, OperationLogger
from .metrics_decorator import MetricsDecorator, PerformanceMetricsDecorator
from .validation_decorator import ValidationDecorator, BusinessValidationDecorator
from .cache_decorator import CacheDecorator, SmartCacheDecorator
from .retry_decorator import RetryDecorator, CircuitBreakerDecorator, ResilientDecorator


class DecoratorFactory:
    """Factory for creating and composing decorators - Factory Pattern"""
    
    @staticmethod
    def create_service_decorator(
        module_name: str,
        operation_name: str,
        config: Dict[str, Any] = None
    ) -> IServiceDecorator:
        """Create a standard service decorator with common cross-cutting concerns"""
        
        config = config or {}
        decorators = []
        
        # Validation (first - fail fast)
        if config.get('validation', True):
            validation_config = config.get('validation_config', {})
            decorators.append(ValidationDecorator(
                validate_inputs=validation_config.get('validate_inputs', True),
                validate_outputs=validation_config.get('validate_outputs', False),
                strict_typing=validation_config.get('strict_typing', False)
            ))
        
        # Caching (before business logic)
        if config.get('cache', False):
            cache_config = config.get('cache_config', {})
            if cache_config.get('smart_cache', False):
                decorators.append(SmartCacheDecorator(
                    base_ttl_seconds=cache_config.get('ttl_seconds', 300),
                    max_ttl_seconds=cache_config.get('max_ttl_seconds', 3600)
                ))
            else:
                decorators.append(CacheDecorator(
                    ttl_seconds=cache_config.get('ttl_seconds', 300)
                ))
        
        # Retry/Resilience (around business logic)
        if config.get('retry', False):
            retry_config = config.get('retry_config', {})
            if retry_config.get('circuit_breaker', False):
                decorators.append(ResilientDecorator(
                    circuit_breaker_threshold=retry_config.get('failure_threshold', 5),
                    circuit_breaker_timeout=retry_config.get('timeout_seconds', 60.0)
                ))
            else:
                decorators.append(RetryDecorator(
                    max_attempts=retry_config.get('max_attempts', 3),
                    base_delay_seconds=retry_config.get('base_delay', 1.0)
                ))
        
        # Metrics (around everything for complete measurement)
        if config.get('metrics', True):
            metrics_config = config.get('metrics_config', {})
            if metrics_config.get('performance_monitoring', False):
                decorators.append(PerformanceMetricsDecorator(
                    operation_name=operation_name,
                    module_name=module_name,
                    threshold_ms=metrics_config.get('threshold_ms', 1000.0)
                ))
            else:
                decorators.append(MetricsDecorator(
                    operation_name=operation_name,
                    module_name=module_name,
                    collect_args_metrics=metrics_config.get('collect_args', False),
                    collect_result_metrics=metrics_config.get('collect_results', False)
                ))
        
        # Logging (outermost - capture everything)
        if config.get('logging', True):
            logging_config = config.get('logging_config', {})
            if logging_config.get('operation_logging', False):
                decorators.append(OperationLogger(
                    operation_type=operation_name,
                    module_name=module_name
                ))
            else:
                decorators.append(LoggingDecorator(
                    logger_name=f"{module_name}.{operation_name}",
                    include_args=logging_config.get('include_args', True),
                    include_result=logging_config.get('include_result', False)
                ))
        
        return CompositeDecorator(decorators)
    
    @staticmethod
    def create_read_operation_decorator(module_name: str, operation_name: str) -> IServiceDecorator:
        """Create decorator optimized for read operations"""
        return DecoratorFactory.create_service_decorator(
            module_name=module_name,
            operation_name=operation_name,
            config={
                'validation': True,
                'cache': True,
                'cache_config': {
                    'smart_cache': True,
                    'ttl_seconds': 300
                },
                'retry': True,
                'retry_config': {
                    'max_attempts': 2,
                    'base_delay': 0.5
                },
                'metrics': True,
                'logging': True,
                'logging_config': {
                    'include_args': False,
                    'include_result': False
                }
            }
        )
    
    @staticmethod
    def create_write_operation_decorator(module_name: str, operation_name: str) -> IServiceDecorator:
        """Create decorator optimized for write operations"""
        return DecoratorFactory.create_service_decorator(
            module_name=module_name,
            operation_name=operation_name,
            config={
                'validation': True,
                'validation_config': {
                    'validate_inputs': True,
                    'validate_outputs': True,
                    'strict_typing': True
                },
                'cache': False,  # Don't cache write operations
                'retry': True,
                'retry_config': {
                    'max_attempts': 3,
                    'base_delay': 1.0,
                    'circuit_breaker': True
                },
                'metrics': True,
                'metrics_config': {
                    'performance_monitoring': True,
                    'collect_args': True,
                    'collect_results': True
                },
                'logging': True,
                'logging_config': {
                    'operation_logging': True,
                    'include_args': True,
                    'include_result': True
                }
            }
        )
    
    @staticmethod
    def create_processing_operation_decorator(module_name: str, operation_name: str) -> IServiceDecorator:
        """Create decorator optimized for processing operations"""
        return DecoratorFactory.create_service_decorator(
            module_name=module_name,
            operation_name=operation_name,
            config={
                'validation': True,
                'validation_config': {
                    'validate_inputs': True,
                    'strict_typing': True
                },
                'cache': False,  # Processing operations shouldn't be cached
                'retry': True,
                'retry_config': {
                    'max_attempts': 2,
                    'base_delay': 2.0,
                    'circuit_breaker': True,
                    'failure_threshold': 3
                },
                'metrics': True,
                'metrics_config': {
                    'performance_monitoring': True,
                    'threshold_ms': 5000.0,  # Higher threshold for processing
                    'collect_args': True,
                    'collect_results': True
                },
                'logging': True,
                'logging_config': {
                    'operation_logging': True,
                    'include_args': True,
                    'include_result': False  # Results might be large
                }
            }
        )


def service_operation(
    operation_type: str = "generic",
    module_name: str = None,
    operation_name: str = None,
    **config_overrides
):
    """
    Decorator function for easy application to service methods
    
    Usage:
    @service_operation("read", "media_management", "get_media_by_id")
    async def get_media_by_id(self, media_id: UUID) -> Optional[Media]:
        pass
    """
    def decorator_wrapper(func: Callable) -> Callable:
        # Infer module and operation names if not provided
        inferred_module = module_name or getattr(func, '__module__', 'unknown').split('.')[-2]
        inferred_operation = operation_name or func.__name__
        
        # Select appropriate decorator factory method
        factory_method = {
            'read': DecoratorFactory.create_read_operation_decorator,
            'write': DecoratorFactory.create_write_operation_decorator, 
            'processing': DecoratorFactory.create_processing_operation_decorator,
            'generic': DecoratorFactory.create_service_decorator
        }.get(operation_type, DecoratorFactory.create_service_decorator)
        
        # Create decorator
        if operation_type == "generic":
            decorator = factory_method(inferred_module, inferred_operation, config_overrides)
        else:
            decorator = factory_method(inferred_module, inferred_operation)
        
        return decorator.decorate(func)
    
    return decorator_wrapper


# Convenience decorators for common patterns
def read_operation(module_name: str = None, operation_name: str = None):
    """Decorator for read operations with caching and retry"""
    return service_operation("read", module_name, operation_name)


def write_operation(module_name: str = None, operation_name: str = None):
    """Decorator for write operations with validation and metrics"""
    return service_operation("write", module_name, operation_name)


def processing_operation(module_name: str = None, operation_name: str = None):
    """Decorator for processing operations with resilience and monitoring"""
    return service_operation("processing", module_name, operation_name)