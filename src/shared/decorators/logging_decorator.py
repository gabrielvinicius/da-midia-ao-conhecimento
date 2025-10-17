"""
Logging Decorator for automatic operation logging
"""
import logging
import time
import json
from typing import Any, Optional
from uuid import UUID
from .base_decorator import BaseAsyncDecorator


class LoggingDecorator(BaseAsyncDecorator):
    """Decorator for automatic function logging"""
    
    def __init__(
        self, 
        logger_name: str = "service",
        log_level: int = logging.INFO,
        include_args: bool = True,
        include_result: bool = False,
        sensitive_params: list[str] = None
    ):
        super().__init__("logging")
        self.logger = logging.getLogger(logger_name)
        self.log_level = log_level
        self.include_args = include_args
        self.include_result = include_result
        self.sensitive_params = sensitive_params or ['password', 'token', 'secret', 'key']
        self.start_time = None
    
    async def _before_execution(self, *args, **kwargs) -> Optional[Any]:
        """Log function entry"""
        self.start_time = time.time()
        
        # Get function name from call stack
        func_name = self._get_function_name(*args)
        
        log_data = {
            "event": "function_start",
            "function": func_name,
            "timestamp": self.start_time
        }
        
        if self.include_args:
            log_data["args"] = self._sanitize_args(args, kwargs)
        
        self.logger.log(self.log_level, f"Starting {func_name}", extra=log_data)
        return None
    
    async def _after_execution(self, result: Any, *args, **kwargs) -> Any:
        """Log successful function completion"""
        end_time = time.time()
        duration = end_time - self.start_time if self.start_time else 0
        
        func_name = self._get_function_name(*args)
        
        log_data = {
            "event": "function_success", 
            "function": func_name,
            "duration_ms": round(duration * 1000, 2),
            "timestamp": end_time
        }
        
        if self.include_result and result is not None:
            log_data["result_type"] = type(result).__name__
            if hasattr(result, 'id'):
                log_data["result_id"] = str(result.id)
        
        self.logger.log(self.log_level, f"Completed {func_name} in {duration:.3f}s", extra=log_data)
        return result
    
    async def _on_exception(self, exception: Exception, *args, **kwargs) -> None:
        """Log function exceptions"""
        end_time = time.time()
        duration = end_time - self.start_time if self.start_time else 0
        
        func_name = self._get_function_name(*args)
        
        log_data = {
            "event": "function_error",
            "function": func_name,
            "duration_ms": round(duration * 1000, 2),
            "error_type": type(exception).__name__,
            "error_message": str(exception),
            "timestamp": end_time
        }
        
        if self.include_args:
            log_data["args"] = self._sanitize_args(args, kwargs)
        
        self.logger.error(f"Failed {func_name} after {duration:.3f}s: {exception}", extra=log_data)
    
    def _get_function_name(self, *args) -> str:
        """Extract function name from arguments"""
        if args and hasattr(args[0], '__class__'):
            return f"{args[0].__class__.__name__}.{args[0].__class__.__name__}"
        return "unknown_function"
    
    def _sanitize_args(self, args: tuple, kwargs: dict) -> dict:
        """Sanitize arguments removing sensitive data"""
        sanitized = {"args_count": len(args)}
        
        # Sanitize kwargs
        sanitized_kwargs = {}
        for key, value in kwargs.items():
            if any(sensitive in key.lower() for sensitive in self.sensitive_params):
                sanitized_kwargs[key] = "***REDACTED***"
            elif isinstance(value, (str, int, float, bool, type(None))):
                sanitized_kwargs[key] = value
            elif isinstance(value, UUID):
                sanitized_kwargs[key] = str(value)
            else:
                sanitized_kwargs[key] = f"<{type(value).__name__}>"
        
        sanitized["kwargs"] = sanitized_kwargs
        return sanitized


class OperationLogger(LoggingDecorator):
    """Specialized logger for business operations"""
    
    def __init__(self, operation_type: str, module_name: str):
        super().__init__(
            logger_name=f"{module_name}.operations",
            log_level=logging.INFO,
            include_args=True,
            include_result=True
        )
        self.operation_type = operation_type
        self.module_name = module_name
    
    async def _before_execution(self, *args, **kwargs) -> Optional[Any]:
        """Log operation start with business context"""
        self.start_time = time.time()
        
        log_data = {
            "event": "operation_start",
            "operation_type": self.operation_type,
            "module": self.module_name,
            "timestamp": self.start_time
        }
        
        # Extract business identifiers
        if args:
            for arg in args:
                if hasattr(arg, 'id'):
                    log_data["entity_id"] = str(arg.id)
                    break
        
        if 'user_id' in kwargs:
            log_data["user_id"] = str(kwargs['user_id'])
        
        self.logger.info(f"Starting {self.operation_type} operation", extra=log_data)
        return None
    
    async def _after_execution(self, result: Any, *args, **kwargs) -> Any:
        """Log operation success with business metrics"""
        end_time = time.time()
        duration = end_time - self.start_time if self.start_time else 0
        
        log_data = {
            "event": "operation_success",
            "operation_type": self.operation_type,
            "module": self.module_name,
            "duration_ms": round(duration * 1000, 2),
            "timestamp": end_time
        }
        
        # Extract result metrics
        if result:
            if hasattr(result, 'id'):
                log_data["result_id"] = str(result.id)
            if hasattr(result, 'status'):
                log_data["result_status"] = result.status
            if isinstance(result, list):
                log_data["result_count"] = len(result)
        
        self.logger.info(f"Completed {self.operation_type} operation successfully", extra=log_data)
        return result