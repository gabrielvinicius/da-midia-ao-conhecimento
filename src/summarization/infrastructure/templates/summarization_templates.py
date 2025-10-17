# src/summarization/application/services/simplified_summarization_template.py
"""
Simplified Summarization Template - Replacement for 514-line God Class
Composes the broken-down components following Single Responsibility Principle
"""

from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

from src.summarization.infrastructure.templates.summarization_templates import SummarizationInput, SummaryType
from src.summarization.domain.summary import Summary
from .summarization_validator import SummarizationValidator, summarization_validator
from .summarization_processor import SummarizationProcessor, summarization_processor
from .summarization_metrics_collector import SummarizationMetricsCollector, summarization_metrics_collector
from src.shared.infrastructure.logging_config import get_logger
from src.shared.patterns.template_method import TemplateMethodBase

logger = get_logger("simplified_summarization_template")


class SimplifiedSummarizationTemplate(TemplateMethodBase[SummarizationInput, Summary]):
    """
    Simplified Summarization Template following SOLID principles
    
    Replaces the original 514-line BaseSummarizationTemplate God Class with composition of focused components:
    - SummarizationValidator: Input validation and constraint checking
    - SummarizationProcessor: Core summarization processing
    - SummarizationMetricsCollector: Metrics collection and quality assessment
    
    This class provides the same template method pattern but with much better separation of concerns.
    """
    
    def __init__(self, provider_name: str, model_name: str = None):
        super().__init__(f"{provider_name}SummarizationTemplate")
        self.provider_name = provider_name
        self.model_name = model_name or "default"
        
        # Compose focused components
        self.validator = summarization_validator
        self.processor = SummarizationProcessor(provider_name, model_name)
        self.metrics = summarization_metrics_collector
        
        # State tracking
        self.metrics_session_id: Optional[str] = None
        
        logger.info(f"Initialized simplified summarization template: {provider_name}")
    
    # === Template Method Implementation ===
    
    async def _initialize(self, input_data: SummarizationInput, options: Dict[str, Any]) -> Any:
        """Initialize summarization session"""
        
        # Add provider metadata to processing result
        self.processing_result.add_metadata("provider", self.provider_name)
        self.processing_result.add_metadata("model", self.model_name)
        self.processing_result.add_metadata("language", input_data.language)
        self.processing_result.add_metadata("summary_type", input_data.summary_type.value)
        self.processing_result.add_metadata("summary_length", input_data.summary_length.value)
        
        # Start metrics collection
        self.metrics_session_id = self.metrics.start_summarization_metrics(input_data, options)
        
        # Initialize provider-specific resources
        await self._initialize_provider(input_data, options)
        
        return {
            "provider": self.provider_name,
            "model": self.model_name,
            "metrics_session": self.metrics_session_id
        }
    
    async def _validate(self, input_data: SummarizationInput, options: Dict[str, Any]) -> bool:
        """Validate summarization input using specialized validator"""
        
        try:
            is_valid, errors = await self.validator.validate_input(input_data, options)
            
            if not is_valid:
                for error in errors:
                    self.processing_result.add_error(error)
                
                logger.warning(f"Summarization validation failed: {len(errors)} errors")
                return False
            
            logger.info("Summarization validation passed")
            return True
            
        except Exception as e:
            error_msg = f"Validation error: {str(e)}"
            self.processing_result.add_error(error_msg)
            logger.error(error_msg)
            return False
    
    async def _process(self, input_data: SummarizationInput, options: Dict[str, Any]) -> Summary:
        """Process summarization using specialized processor"""
        
        try:
            # Use the processor component for actual processing
            result = await self.processor.process_summarization(input_data, options)
            
            # Record successful processing metrics
            if self.metrics_session_id:
                metrics_report = self.metrics.record_summarization_completed(
                    self.metrics_session_id, result, input_data
                )
                result.metrics = metrics_report
            
            logger.info(f"Summarization completed successfully: {input_data.summary_type.value}")
            return result
            
        except Exception as e:
            error_msg = f"Processing error: {str(e)}"
            
            # Record failure metrics if metrics system is available
            if self.metrics_session_id and hasattr(self.metrics, 'record_summarization_failed'):
                self.metrics.record_summarization_failed(self.metrics_session_id, error_msg)
            
            logger.error(error_msg)
            raise
    
    async def _finalize(self, result: Summary, input_data: SummarizationInput, options: Dict[str, Any]) -> Summary:
        """Finalize processing with additional metadata"""
        
        # Add final metadata
        if not hasattr(result, 'processing_metadata'):
            result.processing_metadata = {}
        
        result.processing_metadata.update({
            "provider": self.provider_name,
            "model": self.model_name,
            "template_version": "simplified",
            "validation_config": self.validator.get_validation_config()
        })
        
        # Add processing summary to metadata
        if hasattr(result, 'metrics'):
            self.processing_result.add_metadata("compression_ratio", result.metrics.get("compression", {}).get("compression_ratio", 0))
            self.processing_result.add_metadata("overall_score", result.metrics.get("overall_score", 0))
        
        logger.info(f"Summarization finalized: {self.provider_name}")
        return result
    
    # === Abstract methods that providers must implement ===
    
    @abstractmethod
    async def _initialize_provider(self, input_data: SummarizationInput, options: Dict[str, Any]) -> None:
        """Initialize provider-specific resources"""
        pass
    
    # === Convenience methods for common operations ===
    
    async def validate_only(self, input_data: SummarizationInput, options: Dict[str, Any] = None) -> tuple[bool, list]:
        """Validate input without processing"""
        options = options or {}
        return await self.validator.validate_input(input_data, options)
    
    def get_metrics_summary(self, limit: int = 10) -> Dict[str, Any]:
        """Get processing metrics summary"""
        return self.metrics.get_metrics_summary(limit)
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get provider information"""
        return {
            "provider_name": self.provider_name,
            "model_name": self.model_name,
            "template_name": self.name,
            "validator_config": self.validator.get_validation_config(),
            "processor_stats": self.processor.get_processing_stats() if hasattr(self.processor, 'get_processing_stats') else {}
        }


class OpenAISummarizationTemplate(SimplifiedSummarizationTemplate):
    """
    OpenAI-specific summarization template
    Simplified version of the original implementation
    """
    
    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        super().__init__("openai", model_name)
    
    async def _initialize_provider(self, input_data: SummarizationInput, options: Dict[str, Any]) -> None:
        """Initialize OpenAI-specific resources"""
        
        # Mock OpenAI initialization
        logger.info(f"OpenAI provider initialized with model: {self.model_name}")
        
        # Set OpenAI-specific options
        options.setdefault("max_tokens", 150)
        options.setdefault("temperature", 0.3)


class HuggingFaceSummarizationTemplate(SimplifiedSummarizationTemplate):
    """
    HuggingFace-specific summarization template
    Simplified version of the original implementation
    """
    
    def __init__(self, model_name: str = "facebook/bart-large-cnn"):
        super().__init__("huggingface", model_name)
    
    async def _initialize_provider(self, input_data: SummarizationInput, options: Dict[str, Any]) -> None:
        """Initialize HuggingFace-specific resources"""
        
        # Mock HuggingFace initialization
        logger.info(f"HuggingFace provider initialized with model: {self.model_name}")
        
        # Set HuggingFace-specific options
        options.setdefault("max_length", 142)
        options.setdefault("min_length", 56)
        options.setdefault("do_sample", False)


# Backward compatibility - alias for the original God Class name
BaseSummarizationTemplate = SimplifiedSummarizationTemplate

# Default instances
default_summarization_template = SimplifiedSummarizationTemplate("default")
openai_summarization_template = OpenAISummarizationTemplate()
huggingface_summarization_template = HuggingFaceSummarizationTemplate()