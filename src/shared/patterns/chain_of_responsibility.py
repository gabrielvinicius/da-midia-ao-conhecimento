"""
Chain of Responsibility Pattern implementation for flexible request processing pipelines
"""
from abc import ABC, abstractmethod
from typing import Any, Optional, List, Dict, Type, TypeVar, Generic
from dataclasses import dataclass
from enum import Enum
import asyncio
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')  # Request type
R = TypeVar('R')  # Response type


class HandlerResult(Enum):
    """Result of handler processing"""
    CONTINUE = "continue"  # Continue to next handler
    STOP = "stop"  # Stop processing (success)
    ABORT = "abort"  # Abort processing (failure)


@dataclass
class ProcessingContext:
    """Context passed through the chain"""
    request: Any
    response: Any = None
    metadata: Dict[str, Any] = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.errors is None:
            self.errors = []
    
    def add_error(self, error: str) -> None:
        """Add error to context"""
        self.errors.append(error)
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to context"""
        self.metadata[key] = value
    
    def has_errors(self) -> bool:
        """Check if context has errors"""
        return len(self.errors) > 0


class IChainHandler(ABC, Generic[T, R]):
    """Base interface for chain handlers"""
    
    def __init__(self, name: str = None):
        self.name = name or self.__class__.__name__
        self._next_handler: Optional['IChainHandler'] = None
    
    def set_next(self, handler: 'IChainHandler') -> 'IChainHandler':
        """Set the next handler in the chain"""
        self._next_handler = handler
        return handler
    
    async def handle(self, context: ProcessingContext) -> ProcessingContext:
        """Handle request and potentially pass to next handler"""
        try:
            # Process current handler
            result = await self.process(context)
            
            # Log processing result
            logger.debug(
                f"Handler {self.name} processed with result: {result}",
                extra={
                    "handler": self.name,
                    "result": result.value,
                    "has_errors": context.has_errors()
                }
            )
            
            # Determine next action based on result
            if result == HandlerResult.CONTINUE and self._next_handler:
                return await self._next_handler.handle(context)
            elif result == HandlerResult.ABORT:
                context.add_error(f"Processing aborted by handler: {self.name}")
                return context
            else:  # STOP or end of chain
                return context
                
        except Exception as e:
            logger.error(
                f"Handler {self.name} failed with error: {e}",
                extra={
                    "handler": self.name,
                    "error": str(e),
                    "error_type": type(e).__name__
                },
                exc_info=True
            )
            context.add_error(f"Handler {self.name} failed: {str(e)}")
            return context
    
    @abstractmethod
    async def process(self, context: ProcessingContext) -> HandlerResult:
        """Process the request in this handler"""
        pass
    
    def can_handle(self, context: ProcessingContext) -> bool:
        """Check if this handler can process the request"""
        return True


class BaseChainHandler(IChainHandler[T, R]):
    """Base implementation of chain handler"""
    
    async def process(self, context: ProcessingContext) -> HandlerResult:
        """Default implementation - override in subclasses"""
        return HandlerResult.CONTINUE


class ValidationHandler(BaseChainHandler):
    """Base validation handler"""
    
    def __init__(self, name: str = None, required_fields: List[str] = None):
        super().__init__(name)
        self.required_fields = required_fields or []
    
    async def process(self, context: ProcessingContext) -> HandlerResult:
        """Validate request"""
        if not await self.validate(context):
            return HandlerResult.ABORT
        return HandlerResult.CONTINUE
    
    @abstractmethod
    async def validate(self, context: ProcessingContext) -> bool:
        """Perform validation - return True if valid"""
        pass


class TransformationHandler(BaseChainHandler):
    """Base transformation handler"""
    
    async def process(self, context: ProcessingContext) -> HandlerResult:
        """Transform request"""
        await self.transform(context)
        return HandlerResult.CONTINUE
    
    @abstractmethod
    async def transform(self, context: ProcessingContext) -> None:
        """Perform transformation"""
        pass


class FilterHandler(BaseChainHandler):
    """Base filter handler"""
    
    async def process(self, context: ProcessingContext) -> HandlerResult:
        """Filter request"""
        if not await self.should_continue(context):
            return HandlerResult.STOP
        return HandlerResult.CONTINUE
    
    @abstractmethod
    async def should_continue(self, context: ProcessingContext) -> bool:
        """Check if processing should continue"""
        pass


class ConditionalHandler(BaseChainHandler):
    """Handler that executes based on condition"""
    
    def __init__(self, name: str, condition_func: callable, handler: IChainHandler):
        super().__init__(name)
        self.condition_func = condition_func
        self.conditional_handler = handler
    
    async def process(self, context: ProcessingContext) -> HandlerResult:
        """Execute conditional handler if condition is met"""
        if self.condition_func(context):
            result = await self.conditional_handler.process(context)
            if result == HandlerResult.ABORT:
                return HandlerResult.ABORT
        return HandlerResult.CONTINUE


class ChainBuilder:
    """Builder for creating processing chains"""
    
    def __init__(self, name: str = "ProcessingChain"):
        self.name = name
        self._handlers: List[IChainHandler] = []
        self._built_chain: Optional[IChainHandler] = None
    
    def add_handler(self, handler: IChainHandler) -> 'ChainBuilder':
        """Add handler to the chain"""
        self._handlers.append(handler)
        self._built_chain = None  # Invalidate built chain
        return self
    
    def add_validation(self, validator: ValidationHandler) -> 'ChainBuilder':
        """Add validation handler"""
        return self.add_handler(validator)
    
    def add_transformation(self, transformer: TransformationHandler) -> 'ChainBuilder':
        """Add transformation handler"""
        return self.add_handler(transformer)
    
    def add_filter(self, filter_handler: FilterHandler) -> 'ChainBuilder':
        """Add filter handler"""
        return self.add_handler(filter_handler)
    
    def add_conditional(
        self, 
        condition: callable, 
        handler: IChainHandler, 
        name: str = "ConditionalHandler"
    ) -> 'ChainBuilder':
        """Add conditional handler"""
        conditional = ConditionalHandler(name, condition, handler)
        return self.add_handler(conditional)
    
    def build(self) -> IChainHandler:
        """Build the chain by linking handlers"""
        if self._built_chain:
            return self._built_chain
        
        if not self._handlers:
            raise ValueError("Cannot build empty chain")
        
        # Link handlers
        for i in range(len(self._handlers) - 1):
            self._handlers[i].set_next(self._handlers[i + 1])
        
        self._built_chain = self._handlers[0]
        
        logger.info(
            f"Built processing chain '{self.name}' with {len(self._handlers)} handlers",
            extra={
                "chain_name": self.name,
                "handler_count": len(self._handlers),
                "handlers": [h.name for h in self._handlers]
            }
        )
        
        return self._built_chain


class ProcessingPipeline:
    """High-level pipeline that uses chain of responsibility"""
    
    def __init__(self, name: str, chain: IChainHandler):
        self.name = name
        self.chain = chain
        self._metrics = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "aborted": 0
        }
    
    async def process(self, request: Any) -> ProcessingContext:
        """Process request through the chain"""
        context = ProcessingContext(request=request)
        
        logger.info(
            f"Starting pipeline '{self.name}' processing",
            extra={
                "pipeline": self.name,
                "request_type": type(request).__name__
            }
        )
        
        try:
            # Process through chain
            result_context = await self.chain.handle(context)
            
            # Update metrics
            self._metrics["total_processed"] += 1
            
            if result_context.has_errors():
                self._metrics["failed"] += 1
                logger.warning(
                    f"Pipeline '{self.name}' completed with errors",
                    extra={
                        "pipeline": self.name,
                        "errors": result_context.errors
                    }
                )
            else:
                self._metrics["successful"] += 1
                logger.info(
                    f"Pipeline '{self.name}' completed successfully",
                    extra={
                        "pipeline": self.name,
                        "metadata": result_context.metadata
                    }
                )
            
            return result_context
            
        except Exception as e:
            self._metrics["total_processed"] += 1
            self._metrics["aborted"] += 1
            
            logger.error(
                f"Pipeline '{self.name}' aborted with exception",
                extra={
                    "pipeline": self.name,
                    "error": str(e),
                    "error_type": type(e).__name__
                },
                exc_info=True
            )
            
            context.add_error(f"Pipeline aborted: {str(e)}")
            return context
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get pipeline processing metrics"""
        total = self._metrics["total_processed"]
        return {
            **self._metrics,
            "success_rate": (self._metrics["successful"] / total * 100) if total > 0 else 0,
            "error_rate": (self._metrics["failed"] / total * 100) if total > 0 else 0
        }


class PipelineRegistry:
    """Registry for managing multiple pipelines - Registry Pattern"""
    
    _pipelines: Dict[str, ProcessingPipeline] = {}
    
    @classmethod
    def register_pipeline(cls, name: str, pipeline: ProcessingPipeline):
        """Register a pipeline"""
        cls._pipelines[name] = pipeline
        logger.info(f"Registered pipeline: {name}")
    
    @classmethod
    def get_pipeline(cls, name: str) -> Optional[ProcessingPipeline]:
        """Get pipeline by name"""
        return cls._pipelines.get(name)
    
    @classmethod
    def get_all_pipelines(cls) -> Dict[str, ProcessingPipeline]:
        """Get all registered pipelines"""
        return cls._pipelines.copy()
    
    @classmethod
    def get_metrics_summary(cls) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all pipelines"""
        return {
            name: pipeline.get_metrics() 
            for name, pipeline in cls._pipelines.items()
        }