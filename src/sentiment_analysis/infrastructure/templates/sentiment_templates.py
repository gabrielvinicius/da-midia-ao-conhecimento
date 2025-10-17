# src/sentiment_analysis/application/services/simplified_sentiment_template.py
"""
Simplified Sentiment Analysis Template - Replacement for 517-line God Class
Composes the broken-down components following Single Responsibility Principle
"""

from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

from src.sentiment_analysis.infrastructure.templates.sentiment_templates import SentimentInput, SentimentLabel
from src.sentiment_analysis.domain.sentiment_analysis import SentimentAnalysis
from .sentiment_validator import SentimentValidator, sentiment_validator
from .sentiment_analyzer import SentimentAnalyzer, sentiment_analyzer
from .sentiment_metrics_collector import SentimentMetricsCollector, sentiment_metrics_collector
from src.shared.infrastructure.logging_config import get_logger
from src.shared.patterns.template_method import TemplateMethodBase

logger = get_logger("simplified_sentiment_template")


class SimplifiedSentimentAnalysisTemplate(TemplateMethodBase[SentimentInput, SentimentAnalysis]):
    """
    Simplified Sentiment Analysis Template following SOLID principles
    
    Replaces the original 517-line BaseSentimentAnalysisTemplate God Class with composition of focused components:
    - SentimentValidator: Input validation and constraint checking
    - SentimentAnalyzer: Core sentiment analysis processing
    - SentimentMetricsCollector: Metrics collection and quality assessment
    
    This class provides the same template method pattern but with much better separation of concerns.
    """
    
    def __init__(self, provider_name: str, model_name: str = None):
        super().__init__(f"{provider_name}SentimentAnalysisTemplate")
        self.provider_name = provider_name
        self.model_name = model_name or "default"
        
        # Compose focused components
        self.validator = sentiment_validator
        self.analyzer = SentimentAnalyzer(provider_name, model_name)
        self.metrics = sentiment_metrics_collector
        
        # State tracking
        self.metrics_session_id: Optional[str] = None
        
        logger.info(f"Initialized simplified sentiment template: {provider_name}")
    
    # === Template Method Implementation ===
    
    async def _initialize(self, input_data: SentimentInput, options: Dict[str, Any]) -> Any:
        """Initialize sentiment analysis session"""
        
        # Add provider metadata to processing result
        self.processing_result.add_metadata("provider", self.provider_name)
        self.processing_result.add_metadata("model", self.model_name)
        self.processing_result.add_metadata("language", input_data.language)
        self.processing_result.add_metadata("granularity", input_data.granularity.value)
        
        # Start metrics collection
        self.metrics_session_id = self.metrics.start_analysis_metrics(input_data, options)
        
        # Initialize provider-specific resources
        await self._initialize_provider(input_data, options)
        
        return {
            "provider": self.provider_name,
            "model": self.model_name,
            "metrics_session": self.metrics_session_id
        }
    
    async def _validate(self, input_data: SentimentInput, options: Dict[str, Any]) -> bool:
        """Validate sentiment input using specialized validator"""
        
        try:
            is_valid, errors = await self.validator.validate_input(input_data, options)
            
            if not is_valid:
                for error in errors:
                    self.processing_result.add_error(error)
                
                logger.warning(f"Sentiment validation failed: {len(errors)} errors")
                return False
            
            logger.info("Sentiment validation passed")
            return True
            
        except Exception as e:
            error_msg = f"Validation error: {str(e)}"
            self.processing_result.add_error(error_msg)
            logger.error(error_msg)
            return False
    
    async def _process(self, input_data: SentimentInput, options: Dict[str, Any]) -> SentimentAnalysis:
        """Process sentiment using specialized analyzer"""
        
        try:
            # Use the analyzer component for actual processing
            result = await self.analyzer.analyze_sentiment(input_data, options)
            
            # Record successful processing metrics
            if self.metrics_session_id:
                metrics_report = self.metrics.record_analysis_completed(
                    self.metrics_session_id, result, input_data
                )
                result.metrics = metrics_report
            
            logger.info(f"Sentiment analysis completed successfully: {input_data.granularity.value}")
            return result
            
        except Exception as e:
            error_msg = f"Processing error: {str(e)}"
            
            # Record failure metrics
            if self.metrics_session_id:
                self.metrics.record_analysis_failed(self.metrics_session_id, error_msg)
            
            logger.error(error_msg)
            raise
    
    async def _finalize(self, result: SentimentAnalysis, input_data: SentimentInput, options: Dict[str, Any]) -> SentimentAnalysis:
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
            self.processing_result.add_metadata("quality_score", result.metrics.get("overall_score", 0))
            self.processing_result.add_metadata("processing_duration", result.metrics.get("processing_duration", 0))
        
        logger.info(f"Sentiment analysis finalized: {self.provider_name}")
        return result
    
    # === Abstract methods that providers must implement ===
    
    @abstractmethod
    async def _initialize_provider(self, input_data: SentimentInput, options: Dict[str, Any]) -> None:
        """Initialize provider-specific resources"""
        pass
    
    # === Convenience methods for common operations ===
    
    async def validate_only(self, input_data: SentimentInput, options: Dict[str, Any] = None) -> tuple[bool, list]:
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
            "analyzer_stats": self.analyzer.get_analysis_stats()
        }


class HuggingFaceSentimentTemplate(SimplifiedSentimentAnalysisTemplate):
    """
    HuggingFace-specific sentiment analysis template
    Simplified version of the original implementation
    """
    
    def __init__(self, model_name: str = "cardiffnlp/twitter-roberta-base-sentiment"):
        super().__init__("huggingface", model_name)
    
    async def _initialize_provider(self, input_data: SentimentInput, options: Dict[str, Any]) -> None:
        """Initialize HuggingFace-specific resources"""
        
        # Mock HuggingFace model loading
        logger.info(f"HuggingFace provider initialized with model: {self.model_name}")
        
        # Set HuggingFace-specific options
        options.setdefault("tokenizer_max_length", 512)
        options.setdefault("return_all_scores", True)


# Backward compatibility - alias for the original God Class name
BaseSentimentAnalysisTemplate = SimplifiedSentimentAnalysisTemplate

# Default instances
default_sentiment_template = SimplifiedSentimentAnalysisTemplate("default")
huggingface_sentiment_template = HuggingFaceSentimentTemplate()