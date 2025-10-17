"""
Integration of Template Method Pattern with existing Decorator and Chain of Responsibility patterns
"""
from typing import Any, Dict, Optional, Callable
from functools import wraps

from src.shared.decorators.base_decorator import BaseAsyncDecorator
from src.shared.patterns.template_method import TemplateMethodBase, TemplateMethodFactory, ProcessingResult


class TemplateMethodDecorator(BaseAsyncDecorator):
    """Decorator that applies Template Method Pattern to service methods"""
    
    def __init__(
        self,
        template_name: str,
        input_builder: Callable = None,
        options_builder: Callable = None,
        result_extractor: Callable = None
    ):
        super().__init__("template_method")
        self.template_name = template_name
        self.input_builder = input_builder or self._default_input_builder
        self.options_builder = options_builder or self._default_options_builder
        self.result_extractor = result_extractor or self._default_result_extractor
        self.template_instance: Optional[TemplateMethodBase] = None
    
    async def _before_execution(self, *args, **kwargs) -> Optional[Any]:
        """Create template instance and build input"""
        
        # Get template from factory
        self.template_instance = TemplateMethodFactory.create_template(self.template_name)
        
        # Build template input
        template_input = self.input_builder(*args, **kwargs)
        
        # Build processing options
        processing_options = self.options_builder(*args, **kwargs)
        
        # Store for use in after_execution
        self._template_input = template_input
        self._processing_options = processing_options
        
        return None  # Continue with normal execution
    
    async def _after_execution(self, result: Any, *args, **kwargs) -> Any:
        """Execute template method and extract result"""
        
        if not self.template_instance:
            return result
        
        try:
            # Execute template method
            template_result = await self.template_instance.execute(
                self._template_input, 
                self._processing_options
            )
            
            # Extract final result
            final_result = self.result_extractor(template_result, result)
            return final_result
            
        except Exception as e:
            # If template method fails, return original result
            return result
    
    async def _on_exception(self, exception: Exception, *args, **kwargs) -> None:
        """Handle template method exceptions"""
        pass
    
    def _default_input_builder(self, *args, **kwargs) -> Any:
        """Default input builder - combine args and kwargs"""
        return {
            "args": args,
            "kwargs": kwargs
        }
    
    def _default_options_builder(self, *args, **kwargs) -> Dict[str, Any]:
        """Default options builder"""
        return kwargs.get("template_options", {})
    
    def _default_result_extractor(self, template_result: ProcessingResult, original_result: Any) -> Any:
        """Default result extractor - return template result if successful"""
        if template_result.success and template_result.result is not None:
            return template_result.result
        return original_result


# Convenience decorators for specific template types
def transcription_template(template_name: str = "whisper_base"):
    """Decorator for transcription services using template methods"""
    
    def input_builder(*args, **kwargs):
        from src.transcription.infrastructure.templates.transcription_templates import TranscriptionInput, AudioFormat
        
        # Extract parameters from method arguments
        audio_data = kwargs.get('audio_data') or (args[1] if len(args) > 1 else b"")
        language = kwargs.get('language', 'en')
        
        return TranscriptionInput(
            audio_data=audio_data,
            language=language,
            audio_format=AudioFormat.WAV
        )
    
    def result_extractor(template_result: ProcessingResult, original_result: Any):
        if template_result.success and template_result.result:
            return template_result.result
        return original_result
    
    def decorator(func):
        template_decorator = TemplateMethodDecorator(
            template_name=template_name,
            input_builder=input_builder,
            result_extractor=result_extractor
        )
        return template_decorator.decorate(func)
    
    return decorator


def summarization_template(template_name: str = "openai_gpt35"):
    """Decorator for summarization services using template methods"""
    
    def input_builder(*args, **kwargs):
        from src.summarization.infrastructure.templates.summarization_templates import (
            SummarizationInput, SummaryType, SummaryLength
        )
        
        text = kwargs.get('text') or (args[1] if len(args) > 1 else "")
        
        return SummarizationInput(
            text=text,
            language=kwargs.get('language', 'en'),
            summary_type=SummaryType(kwargs.get('summary_type', 'abstractive')),
            summary_length=SummaryLength(kwargs.get('summary_length', 'medium'))
        )
    
    def decorator(func):
        template_decorator = TemplateMethodDecorator(
            template_name=template_name,
            input_builder=input_builder
        )
        return template_decorator.decorate(func)
    
    return decorator


def sentiment_analysis_template(template_name: str = "hf_roberta_sentiment"):
    """Decorator for sentiment analysis services using template methods"""
    
    def input_builder(*args, **kwargs):
        from src.sentiment_analysis.infrastructure.templates.sentiment_templates import (
            SentimentInput, AnalysisGranularity
        )
        
        text = kwargs.get('text') or (args[1] if len(args) > 1 else "")
        
        return SentimentInput(
            text=text,
            language=kwargs.get('language', 'en'),
            granularity=AnalysisGranularity(kwargs.get('granularity', 'document'))
        )
    
    def decorator(func):
        template_decorator = TemplateMethodDecorator(
            template_name=template_name,
            input_builder=input_builder
        )
        return template_decorator.decorate(func)
    
    return decorator


def video_processing_template(template_name: str = "ffmpeg_standard"):
    """Decorator for video processing services using template methods"""
    
    def input_builder(*args, **kwargs):
        from src.video_processing.infrastructure.templates.video_templates import (
            VideoProcessingInput, VideoOperation, VideoFormat
        )
        
        video_data = kwargs.get('video_data') or (args[1] if len(args) > 1 else b"")
        operation = kwargs.get('operation', 'transcode')
        
        return VideoProcessingInput(
            video_data=video_data,
            operation=VideoOperation(operation),
            input_format=VideoFormat(kwargs.get('input_format', 'mp4')),
            output_format=VideoFormat(kwargs.get('output_format', 'mp4')) if kwargs.get('output_format') else None
        )
    
    def decorator(func):
        template_decorator = TemplateMethodDecorator(
            template_name=template_name,
            input_builder=input_builder
        )
        return template_decorator.decorate(func)
    
    return decorator