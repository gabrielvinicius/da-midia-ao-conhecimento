"""
Integration of Chain of Responsibility with Decorator Pattern
"""
from typing import Any, Dict, Optional
from functools import wraps

from src.shared.decorators.base_decorator import IServiceDecorator, BaseAsyncDecorator
from src.shared.patterns.chain_of_responsibility import (
    ProcessingPipeline, ProcessingContext, PipelineRegistry
)


class PipelineDecorator(BaseAsyncDecorator):
    """Decorator that applies a Chain of Responsibility pipeline to service methods"""
    
    def __init__(
        self,
        pipeline_name: str,
        request_builder: callable = None,
        response_extractor: callable = None
    ):
        super().__init__("pipeline")
        self.pipeline_name = pipeline_name
        self.request_builder = request_builder or self._default_request_builder
        self.response_extractor = response_extractor or self._default_response_extractor
        self.pipeline: Optional[ProcessingPipeline] = None
    
    async def _before_execution(self, *args, **kwargs) -> Optional[Any]:
        """Process request through pipeline before method execution"""
        
        # Get pipeline from registry
        self.pipeline = PipelineRegistry.get_pipeline(self.pipeline_name)
        if not self.pipeline:
            raise ValueError(f"Pipeline '{self.pipeline_name}' not found in registry")
        
        # Build request object
        pipeline_request = self.request_builder(*args, **kwargs)
        
        # Process through pipeline
        context = await self.pipeline.process(pipeline_request)
        
        # Check if pipeline failed
        if context.has_errors():
            raise ValueError(f"Pipeline validation failed: {'; '.join(context.errors)}")
        
        # Store context for post-processing
        self._pipeline_context = context
        
        # Extract any pre-processed data
        return self.response_extractor(context, "pre_execution")
    
    async def _after_execution(self, result: Any, *args, **kwargs) -> Any:
        """Process result through pipeline after method execution"""
        
        if hasattr(self, '_pipeline_context'):
            # Update context with execution result
            self._pipeline_context.response = result
            
            # Extract final result
            final_result = self.response_extractor(self._pipeline_context, "post_execution")
            return final_result if final_result is not None else result
        
        return result
    
    async def _on_exception(self, exception: Exception, *args, **kwargs) -> None:
        """Handle pipeline errors"""
        if hasattr(self, '_pipeline_context'):
            self._pipeline_context.add_error(f"Execution failed: {str(exception)}")
    
    def _default_request_builder(self, *args, **kwargs) -> Any:
        """Default request builder - override for specific use cases"""
        return {
            "args": args,
            "kwargs": kwargs
        }
    
    def _default_response_extractor(self, context: ProcessingContext, phase: str) -> Any:
        """Default response extractor - override for specific use cases"""
        if phase == "pre_execution":
            # Return None to continue with normal execution
            return None
        else:  # post_execution
            # Return the response from context or None to use original result
            return context.response


class MediaUploadPipelineDecorator(PipelineDecorator):
    """Specialized decorator for media upload pipeline"""
    
    def __init__(self, pipeline_name: str = "media_upload_enterprise"):
        super().__init__(
            pipeline_name=pipeline_name,
            request_builder=self._build_media_request,
            response_extractor=self._extract_media_response
        )
    
    def _build_media_request(self, *args, **kwargs):
        """Build MediaUploadRequest from method arguments"""
        from src.media_management.infrastructure.pipelines.upload_pipeline import MediaUploadRequest
        
        # Extract common parameters (adjust based on actual method signature)
        user_id = kwargs.get('user_id') or (args[1] if len(args) > 1 else None)
        file_data = kwargs.get('file_data') or kwargs.get('file') or (args[2] if len(args) > 2 else None)
        filename = kwargs.get('filename') or (args[3] if len(args) > 3 else "unknown")
        
        return MediaUploadRequest(
            user_id=user_id,
            file_data=file_data,
            filename=filename,
            metadata=kwargs.get('metadata', {})
        )
    
    def _extract_media_response(self, context: ProcessingContext, phase: str):
        """Extract media upload response"""
        if phase == "pre_execution":
            # Validation passed, continue with upload
            return None
        else:
            # Add pipeline metadata to response
            if hasattr(context.response, '__dict__'):
                context.response.pipeline_metadata = context.metadata
            return context.response


class TextExtractionPipelineDecorator(PipelineDecorator):
    """Specialized decorator for text extraction pipeline"""
    
    def __init__(self, pipeline_name: str = "text_extraction_advanced"):
        super().__init__(
            pipeline_name=pipeline_name,
            request_builder=self._build_text_request,
            response_extractor=self._extract_text_response
        )
    
    def _build_text_request(self, *args, **kwargs):
        """Build TextExtractionRequest from method arguments"""
        from src.text_processing.infrastructure.pipelines.extraction_pipeline import (
            TextExtractionRequest, TextType
        )
        
        file_data = kwargs.get('file_data') or (args[1] if len(args) > 1 else None)
        file_type = kwargs.get('file_type') or TextType.TXT
        filename = kwargs.get('filename') or (args[2] if len(args) > 2 else "unknown")
        
        return TextExtractionRequest(
            file_data=file_data,
            file_type=file_type,
            filename=filename,
            extraction_options=kwargs.get('options', {})
        )
    
    def _extract_text_response(self, context: ProcessingContext, phase: str):
        """Extract text extraction response"""
        if phase == "pre_execution":
            return None
        else:
            # Return extracted text from pipeline
            extracted_text = context.metadata.get("extracted_text")
            if extracted_text:
                return {
                    "text": extracted_text,
                    "metadata": context.metadata,
                    "quality": context.metadata.get("quality_ratio"),
                    "extraction_method": context.metadata.get("extraction_method")
                }
            return context.response


class AuthPipelineDecorator(PipelineDecorator):
    """Specialized decorator for authentication pipeline"""
    
    def __init__(self, action: str, pipeline_name: str = None):
        if not pipeline_name:
            pipeline_name = f"auth_{action}"
        
        super().__init__(
            pipeline_name=pipeline_name,
            request_builder=lambda *args, **kwargs: self._build_auth_request(action, *args, **kwargs),
            response_extractor=self._extract_auth_response
        )
    
    def _build_auth_request(self, action: str, *args, **kwargs):
        """Build AuthRequest from method arguments"""
        from src.auth.infrastructure.pipelines.auth_pipeline import AuthRequest, AuthAction
        
        return AuthRequest(
            action=AuthAction(action),
            user_id=kwargs.get('user_id'),
            username=kwargs.get('username'),
            email=kwargs.get('email'),
            password=kwargs.get('password'),
            token=kwargs.get('token'),
            resource=kwargs.get('resource'),
            permissions_required=kwargs.get('permissions', []),
            client_ip=kwargs.get('client_ip'),
            user_agent=kwargs.get('user_agent')
        )
    
    def _extract_auth_response(self, context: ProcessingContext, phase: str):
        """Extract authentication response"""
        if phase == "pre_execution":
            return None
        else:
            # Return tokens or authorization result
            tokens = context.metadata.get("tokens")
            if tokens:
                return {
                    "tokens": tokens,
                    "user_info": context.metadata.get("user_info"),
                    "audit_logged": context.metadata.get("audit_logged", False)
                }
            
            # For authorization checks
            permission_check = context.metadata.get("permission_check")
            if permission_check:
                return {
                    "authorized": permission_check == "granted",
                    "user_info": context.metadata.get("user_info")
                }
            
            return context.response


# Convenience decorators for common pipeline patterns
def media_upload_pipeline(pipeline_name: str = "media_upload_enterprise"):
    """Decorator for media upload with pipeline validation"""
    def decorator(func):
        decorator_instance = MediaUploadPipelineDecorator(pipeline_name)
        return decorator_instance.decorate(func)
    return decorator


def text_extraction_pipeline(pipeline_name: str = "text_extraction_advanced"):
    """Decorator for text extraction with pipeline processing"""
    def decorator(func):
        decorator_instance = TextExtractionPipelineDecorator(pipeline_name)
        return decorator_instance.decorate(func)
    return decorator


def auth_pipeline(action: str, pipeline_name: str = None):
    """Decorator for authentication with pipeline validation"""
    def decorator(func):
        decorator_instance = AuthPipelineDecorator(action, pipeline_name)
        return decorator_instance.decorate(func)
    return decorator


# Integration with existing decorator factory
from src.shared.decorators.decorator_factory import DecoratorFactory

class EnhancedDecoratorFactory(DecoratorFactory):
    """Enhanced factory that includes pipeline decorators"""
    
    @staticmethod
    def create_pipeline_service_decorator(
        module_name: str,
        operation_name: str,
        pipeline_name: str,
        config: Dict[str, Any] = None
    ):
        """Create service decorator with pipeline integration"""
        
        # Get base decorator
        base_decorator = DecoratorFactory.create_service_decorator(
            module_name, operation_name, config
        )
        
        # Add pipeline decorator
        pipeline_decorator = PipelineDecorator(pipeline_name)
        
        # Combine decorators
        from src.shared.decorators.base_decorator import CompositeDecorator
        return CompositeDecorator([pipeline_decorator, base_decorator])


# Example usage in service classes
"""
from src.shared.patterns.pipeline_integration import media_upload_pipeline, text_extraction_pipeline, auth_pipeline

class EnhancedMediaService:
    
    @media_upload_pipeline("media_upload_enterprise")
    async def upload_media(self, user_id: UUID, file_data: bytes, filename: str) -> MediaUploadResult:
        # Pipeline will validate file, check quotas, scan for viruses, etc.
        # before this method executes
        pass

class EnhancedTextService:
    
    @text_extraction_pipeline("text_extraction_advanced")
    async def extract_text(self, file_data: bytes, file_type: str, filename: str) -> TextResult:
        # Pipeline will validate file type, detect encoding, extract text, etc.
        pass

class EnhancedAuthService:
    
    @auth_pipeline("login")
    async def authenticate_user(self, username: str, password: str, client_ip: str) -> AuthResult:
        # Pipeline will check rate limits, validate inputs, verify password, generate tokens
        pass
"""