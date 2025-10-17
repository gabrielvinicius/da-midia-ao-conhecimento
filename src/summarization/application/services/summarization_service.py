# src/summarization/application/services/summarization_service.py
"""
Summarization Service following SOLID principles.
Single Responsibility: Handle core summarization orchestration.
"""
import structlog
from typing import Dict, Any, Optional
from uuid import UUID

from src.shared.resilience.circuit_breaker import get_circuit_breaker
from src.summarization.infrastructure.interfaces import ISummarizer
from src.summarization.domain.interfaces import (
    ISummarizationService,
    ISummaryValidator,
    ISummaryMetricsService,
    ISummaryStateManager
)
from src.summarization.domain.summary import Summary
from src.shared.decorators.decorator_factory import processing_operation, read_operation

logger = structlog.get_logger(__name__)


class SummarizationService(ISummarizationService):
    """
    Core summarization service following SOLID principles.
    
    Single Responsibility: Orchestrate summarization workflow.
    Open/Closed: Extensible through provider injection.
    Liskov Substitution: Implements ISummarizationService contract.
    Interface Segregation: Uses specific interfaces for each concern.
    Dependency Inversion: Depends on abstractions, not concretions.
    """
    
    def __init__(
        self,
        summarizer_provider: ISummarizer,
        validator: ISummaryValidator,
        metrics_service: ISummaryMetricsService,
        state_manager: ISummaryStateManager
    ):
        self._provider = summarizer_provider
        self._validator = validator
        self._metrics_service = metrics_service
        self._state_manager = state_manager

    @processing_operation("summarization", "generate_text_summary")
    async def summarize(
        self, 
        text_content: str, 
        summary_id: Optional[UUID] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Summarizes text using the configured provider with validation and monitoring.
        
        Args:
            text_content: Text to summarize
            summary_id: Optional summary ID for tracking
            options: Optional summarization options
            
        Returns:
            str: Generated summary
        """
        if summary_id:
            await self._state_manager.update_status(summary_id, "processing")
        
        try:
            # Validate input
            self._validator.validate_input_text(text_content)
            
            # Record processing start
            if summary_id:
                self._metrics_service.record_processing_start(summary_id)
            
            # Apply circuit breaker protection
            breaker = get_circuit_breaker(f"summarization_{self._provider.provider_name}")
            
            summary_text = await breaker.call_async(
                self._provider.summarize, 
                text_content,
                options or {}
            )
            
            # Validate output
            self._validator.validate_summary_quality(summary_text, text_content)
            
            # Record success metrics
            if summary_id:
                self._metrics_service.record_processing_success(
                    summary_id, 
                    len(text_content), 
                    len(summary_text),
                    self._provider.provider_name
                )
                await self._state_manager.update_status(summary_id, "completed")
            
            logger.info(
                "summarization.completed",
                summary_id=str(summary_id) if summary_id else None,
                input_length=len(text_content),
                output_length=len(summary_text),
                provider=self._provider.provider_name
            )
            
            return summary_text
            
        except Exception as e:
            if summary_id:
                await self._state_manager.update_status(summary_id, "failed", str(e))
                self._metrics_service.record_processing_failure(summary_id, str(e))
            
            logger.error(
                "summarization.failed",
                summary_id=str(summary_id) if summary_id else None,
                error=str(e),
                provider=self._provider.provider_name
            )
            raise

    @processing_operation("summarization", "batch_summarize_texts")
    async def batch_summarize(
        self, 
        texts: Dict[UUID, str], 
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[UUID, str]:
        """
        Summarize multiple texts in batch.
        
        Args:
            texts: Dictionary mapping summary IDs to text content
            options: Optional summarization options
            
        Returns:
            Dict mapping summary IDs to generated summaries
        """
        results = {}
        failed_count = 0
        
        for summary_id, text_content in texts.items():
            try:
                summary = await self.summarize(text_content, summary_id, options)
                results[summary_id] = summary
            except Exception as e:
                failed_count += 1
                logger.warning(
                    "summarization.batch_item_failed",
                    summary_id=str(summary_id),
                    error=str(e)
                )
        
        logger.info(
            "summarization.batch_completed",
            total_items=len(texts),
            successful=len(results),
            failed=failed_count
        )
        
        return results
