"""
Unified providers - eliminating provider pattern duplication
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic
import structlog
from dataclasses import dataclass
from enum import Enum

logger = structlog.get_logger(__name__)

TInput = TypeVar('TInput')
TOutput = TypeVar('TOutput')
TConfig = TypeVar('TConfig')

class ProviderType(str, Enum):
    """Provider types supported"""
    TRANSCRIPTION = "transcription"
    SUMMARIZATION = "summarization"
    TOPIC_MODELING = "topic_modeling"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    STORAGE = "storage"

@dataclass
class ProviderResult:
    """Unified provider result structure"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class ProviderError(Exception):
    """Base provider error"""
    def __init__(self, message: str, provider_name: str, original_error: Exception = None):
        super().__init__(message)
        self.provider_name = provider_name
        self.original_error = original_error

class BaseProvider(ABC, Generic[TInput, TOutput, TConfig]):
    """Base provider eliminating all provider duplication"""
    
    def __init__(self, provider_name: str, provider_type: ProviderType, config: TConfig = None):
        self.provider_name = provider_name
        self.provider_type = provider_type
        self.config = config or {}
        self.logger = logger.bind(provider=provider_name, type=provider_type.value)
    
    async def process(self, input_data: TInput, **kwargs) -> ProviderResult:
        """Unified processing method with error handling and logging"""
        
        operation_id = kwargs.get('operation_id', 'unknown')
        self.logger.info("Processing started", operation_id=operation_id)
        
        try:
            # Validate input
            self._validate_input(input_data)
            
            # Execute provider-specific logic
            result = await self._execute(input_data, **kwargs)
            
            # Validate output
            validated_result = self._validate_output(result)
            
            self.logger.info("Processing completed", operation_id=operation_id)
            
            return ProviderResult(
                success=True,
                data=validated_result,
                metadata={
                    "provider": self.provider_name,
                    "type": self.provider_type.value,
                    "operation_id": operation_id
                }
            )
            
        except Exception as e:
            error_msg = f"Provider {self.provider_name} failed: {str(e)}"
            self.logger.error("Processing failed", error=error_msg, operation_id=operation_id)
            
            return ProviderResult(
                success=False,
                error=error_msg,
                metadata={
                    "provider": self.provider_name,
                    "type": self.provider_type.value,
                    "operation_id": operation_id
                }
            )
    
    @abstractmethod
    async def _execute(self, input_data: TInput, **kwargs) -> TOutput:
        """Provider-specific execution logic"""
        pass
    
    def _validate_input(self, input_data: TInput) -> None:
        """Validate input data - override if needed"""
        if input_data is None:
            raise ProviderError("Input data cannot be None", self.provider_name)
    
    def _validate_output(self, output_data: TOutput) -> TOutput:
        """Validate output data - override if needed"""
        return output_data
    
    async def health_check(self) -> bool:
        """Health check - override if needed"""
        return True
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get provider capabilities - override if needed"""
        return {
            "provider": self.provider_name,
            "type": self.provider_type.value,
            "supports_async": True
        }

# Specific provider types
class TranscriptionProvider(BaseProvider[bytes, Dict[str, Any], Dict]):
    """Base for transcription providers"""
    
    def __init__(self, provider_name: str, config: Dict = None):
        super().__init__(provider_name, ProviderType.TRANSCRIPTION, config)

class SummarizationProvider(BaseProvider[str, str, Dict]):
    """Base for summarization providers"""
    
    def __init__(self, provider_name: str, config: Dict = None):
        super().__init__(provider_name, ProviderType.SUMMARIZATION, config)

class TopicModelingProvider(BaseProvider[str, List[Dict], Dict]):
    """Base for topic modeling providers"""
    
    def __init__(self, provider_name: str, config: Dict = None):
        super().__init__(provider_name, ProviderType.TOPIC_MODELING, config)

# Provider registry
class ProviderRegistry:
    """Unified provider registry"""
    
    def __init__(self):
        self._providers: Dict[str, Dict[str, BaseProvider]] = {
            provider_type.value: {} for provider_type in ProviderType
        }
    
    def register(self, provider: BaseProvider):
        """Register a provider"""
        provider_type = provider.provider_type.value
        self._providers[provider_type][provider.provider_name] = provider
        logger.info(f"Registered {provider.provider_name} for {provider_type}")
    
    def get_provider(self, provider_type: str, provider_name: str) -> Optional[BaseProvider]:
        """Get a specific provider"""
        return self._providers.get(provider_type, {}).get(provider_name)
    
    def get_providers(self, provider_type: str) -> Dict[str, BaseProvider]:
        """Get all providers of a type"""
        return self._providers.get(provider_type, {})
    
    def list_providers(self) -> Dict[str, List[str]]:
        """List all registered providers"""
        return {
            provider_type: list(providers.keys())
            for provider_type, providers in self._providers.items()
        }

# Global registry
provider_registry = ProviderRegistry()

# Provider factory
class ProviderFactory:
    """Unified provider factory"""
    
    @staticmethod
    def create_provider(
        provider_type: ProviderType,
        provider_name: str,
        config: Dict = None
    ) -> BaseProvider:
        """Create provider instance"""
        
        if provider_type == ProviderType.TRANSCRIPTION:
            return TranscriptionProvider(provider_name, config)
        elif provider_type == ProviderType.SUMMARIZATION:
            return SummarizationProvider(provider_name, config)
        elif provider_type == ProviderType.TOPIC_MODELING:
            return TopicModelingProvider(provider_name, config)
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")

# Convenience decorators
def register_provider(provider_type: ProviderType, provider_name: str):
    """Decorator to auto-register providers"""
    def decorator(cls):
        instance = cls(provider_name)
        provider_registry.register(instance)
        return cls
    return decorator
