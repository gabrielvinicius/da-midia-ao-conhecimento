# src/transcription/application/services/simplified_transcription_template.py
"""
Simplified Transcription Template - Replacement for 421-line God Class
Composes the broken-down components following Single Responsibility Principle
"""

from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

from src.transcription.infrastructure.templates.transcription_templates import TranscriptionInput, AudioFormat
from src.transcription.domain.transcription import Transcription
from .transcription_validator import TranscriptionValidator, transcription_validator
from .transcription_processor import TranscriptionProcessor, transcription_processor
from .transcription_metrics_collector import TranscriptionMetricsCollector, transcription_metrics_collector
from src.shared.infrastructure.logging_config import get_logger
from src.shared.patterns.template_method import TemplateMethodBase

logger = get_logger("simplified_transcription_template")


class SimplifiedTranscriptionTemplate(TemplateMethodBase[TranscriptionInput, Transcription]):
    """
    Simplified Transcription Template following SOLID principles
    
    Replaces the original 421-line BaseTranscriptionTemplate God Class with composition of focused components:
    - TranscriptionValidator: Input validation and audio constraint checking
    - TranscriptionProcessor: Core transcription processing and audio handling
    - TranscriptionMetricsCollector: Metrics collection and quality assessment
    
    This class provides the same template method pattern but with much better separation of concerns.
    """
    
    def __init__(self, provider_name: str, model_name: str = None):
        super().__init__(f"{provider_name}TranscriptionTemplate")
        self.provider_name = provider_name
        self.model_name = model_name or "default"
        
        # Compose focused components
        self.validator = transcription_validator
        self.processor = TranscriptionProcessor(provider_name, model_name)
        self.metrics = transcription_metrics_collector
        
        # State tracking
        self.metrics_session_id: Optional[str] = None
        
        logger.info(f"Initialized simplified transcription template: {provider_name}")
    
    # === Template Method Implementation ===
    
    async def _initialize(self, input_data: TranscriptionInput, options: Dict[str, Any]) -> Any:
        """Initialize transcription session"""
        
        # Add provider metadata to processing result
        self.processing_result.add_metadata("provider", self.provider_name)
        self.processing_result.add_metadata("model", self.model_name)
        self.processing_result.add_metadata("language", input_data.language)
        self.processing_result.add_metadata("audio_format", input_data.audio_format.value)
        
        # Start metrics collection
        self.metrics_session_id = self.metrics.start_transcription_metrics(input_data, options)
        
        # Initialize provider-specific resources
        await self._initialize_provider(input_data, options)
        
        return {
            "provider": self.provider_name,
            "model": self.model_name,
            "metrics_session": self.metrics_session_id
        }
    
    async def _validate(self, input_data: TranscriptionInput, options: Dict[str, Any]) -> bool:
        """Validate transcription input using specialized validator"""
        
        try:
            is_valid, errors = await self.validator.validate_input(input_data, options)
            
            if not is_valid:
                for error in errors:
                    self.processing_result.add_error(error)
                
                logger.warning(f"Transcription validation failed: {len(errors)} errors")
                return False
            
            logger.info("Transcription validation passed")
            return True
            
        except Exception as e:
            error_msg = f"Validation error: {str(e)}"
            self.processing_result.add_error(error_msg)
            logger.error(error_msg)
            return False
    
    async def _process(self, input_data: TranscriptionInput, options: Dict[str, Any]) -> Transcription:
        """Process transcription using specialized processor"""
        
        try:
            # Use the processor component for actual processing
            result = await self.processor.process_transcription(input_data, options)
            
            # Record successful processing metrics
            if self.metrics_session_id:
                metrics_report = self.metrics.record_transcription_completed(
                    self.metrics_session_id, result, input_data
                )
                result.metrics = metrics_report
            
            logger.info(f"Transcription completed successfully: {input_data.language}")
            return result
            
        except Exception as e:
            error_msg = f"Processing error: {str(e)}"
            
            # Record failure metrics
            if self.metrics_session_id:
                self.metrics.record_transcription_failed(self.metrics_session_id, error_msg)
            
            logger.error(error_msg)
            raise
    
    async def _finalize(self, result: Transcription, input_data: TranscriptionInput, options: Dict[str, Any]) -> Transcription:
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
            self.processing_result.add_metadata("confidence", result.confidence)
            self.processing_result.add_metadata("overall_score", result.metrics.get("overall_score", 0))
        
        logger.info(f"Transcription finalized: {self.provider_name}")
        return result
    
    # === Abstract methods that providers must implement ===
    
    @abstractmethod
    async def _initialize_provider(self, input_data: TranscriptionInput, options: Dict[str, Any]) -> None:
        """Initialize provider-specific resources"""
        pass
    
    # === Convenience methods for common operations ===
    
    async def validate_only(self, input_data: TranscriptionInput, options: Dict[str, Any] = None) -> tuple[bool, list]:
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
            "processor_stats": self.processor.get_processing_stats()
        }


class WhisperTranscriptionTemplate(SimplifiedTranscriptionTemplate):
    """
    Whisper-specific transcription template
    Simplified version of the original implementation
    """
    
    def __init__(self, model_size: str = "base"):
        super().__init__("whisper", model_size)
        self.model_size = model_size
    
    async def _initialize_provider(self, input_data: TranscriptionInput, options: Dict[str, Any]) -> None:
        """Initialize Whisper-specific resources"""
        
        # Mock Whisper model loading
        logger.info(f"Whisper provider initialized with model: {self.model_size}")
        
        # Set Whisper-specific options
        options.setdefault("word_timestamps", True)
        options.setdefault("temperature", 0)


class FastWhisperTranscriptionTemplate(SimplifiedTranscriptionTemplate):
    """
    FastWhisper-specific transcription template
    Simplified version with performance optimizations
    """
    
    def __init__(self, model_size: str = "base", device: str = "auto"):
        super().__init__("fast_whisper", model_size)
        self.model_size = model_size
        self.device = device
    
    async def _initialize_provider(self, input_data: TranscriptionInput, options: Dict[str, Any]) -> None:
        """Initialize FastWhisper-specific resources"""
        
        # Mock FastWhisper initialization
        logger.info(f"FastWhisper provider initialized: {self.model_size} on {self.device}")
        
        # Set FastWhisper-specific options
        options.setdefault("batch_size", 16)
        options.setdefault("beam_size", 5)


# Backward compatibility - alias for the original God Class name
BaseTranscriptionTemplate = SimplifiedTranscriptionTemplate

# Default instances
default_transcription_template = SimplifiedTranscriptionTemplate("default")
whisper_transcription_template = WhisperTranscriptionTemplate()
fast_whisper_transcription_template = FastWhisperTranscriptionTemplate()