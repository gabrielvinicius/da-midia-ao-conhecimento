# src/sentiment_analysis/application/commands/analyze_sentiment_command_handler.py
import structlog
from typing import Optional

from src.sentiment_analysis.domain.sentiment_analysis import SentimentAnalysisResult
from src.sentiment_analysis.domain.interfaces import ISentimentAnalyzer, SentimentProvider
from src.sentiment_analysis.infrastructure.sentiment_analysis_repository import SentimentAnalysisRepository
from src.sentiment_analysis.infrastructure.dependencies import SentimentServiceFactory
from src.shared.events.event_bus import EventBus
from src.shared.events.domain_events import SentimentAnalysisCompleted
from .analyze_sentiment_command import AnalyzeSentimentCommand

logger = structlog.get_logger(__name__)


class AnalyzeSentimentCommandHandler:
    """
    Command handler for sentiment analysis following SOLID principles.
    
    Single Responsibility: Handle sentiment analysis commands.
    Open/Closed: Extensible through analyzer interfaces.
    Dependency Inversion: Uses abstractions for analyzer and repository.
    """
    
    def __init__(
        self,
        sentiment_analyzer: Optional[ISentimentAnalyzer] = None,
        sentiment_service_factory: Optional[SentimentServiceFactory] = None,
        repository: Optional[SentimentAnalysisRepository] = None,
        event_bus: Optional[EventBus] = None,
    ):
        # New SOLID approach
        self.sentiment_analyzer = sentiment_analyzer
        
        # Legacy compatibility
        self.sentiment_service_factory = sentiment_service_factory
        self.repository = repository
        self.event_bus = event_bus

    async def handle(self, command: AnalyzeSentimentCommand) -> SentimentAnalysisResult:
        """
        Handles the sentiment analysis process.
        
        Uses new analyzer if available, falls back to legacy implementation.
        """
        logger.info("sentiment_analysis.started", media_id=command.media_id, provider=command.provider)

        try:
            if self.sentiment_analyzer:
                # New SOLID approach
                return await self._handle_with_analyzer(command)
            else:
                # Legacy approach for backward compatibility
                return await self._handle_legacy(command)

        except Exception as e:
            logger.error("sentiment_analysis.failed", media_id=command.media_id, error=str(e))
            raise

    async def _handle_with_analyzer(self, command: AnalyzeSentimentCommand) -> SentimentAnalysisResult:
        """Handle command using new sentiment analyzer."""
        # Convert provider string to enum
        try:
            provider = SentimentProvider(command.provider.lower())
        except (ValueError, AttributeError):
            logger.warning(
                "sentiment_analysis.unknown_provider",
                provider=command.provider,
                fallback="huggingface"
            )
            provider = SentimentProvider.HUGGINGFACE
        
        # Use analyzer to process media
        if hasattr(command, 'media_id') and command.media_id:
            options = {}
            if hasattr(command, 'language'):
                options['language'] = command.language
                
            result_id = await self.sentiment_analyzer.analyze_media(
                media_id=command.media_id,
                provider=provider,
                options=options
            )
            
            # Get the saved result
            if self.repository:
                result = await self.repository.find_by_id(result_id)
                if result:
                    # Publish event if event bus available
                    if self.event_bus:
                        await self.event_bus.publish(SentimentAnalysisCompleted(
                            media_id=command.media_id,
                            sentiment_result=result.to_dict()
                        ))
                    
                    logger.info("sentiment_analysis.completed", media_id=command.media_id, result_id=str(result_id))
                    return result
        
        # Fallback: create a basic result
        analysis_result = await self.sentiment_analyzer.analyze_text_directly(
            text=getattr(command, 'text_content', ''),
            provider=provider
        )
        
        result = SentimentAnalysisResult(
            media_id=command.media_id,
            label=analysis_result.get("label", "neutral"),
            score=analysis_result.get("score", 0.0),
            confidence=analysis_result.get("confidence", 0.0),
            provider=provider.value,
            full_result=analysis_result
        )
        
        if self.repository:
            saved_result = await self.repository.save(result)
            return saved_result
        
        return result

    async def _handle_legacy(self, command: AnalyzeSentimentCommand) -> SentimentAnalysisResult:
        """Legacy handler for backward compatibility."""
        if not self.sentiment_service_factory or not self.repository:
            raise ValueError("Legacy dependencies not available")
            
        service = self.sentiment_service_factory(command.provider)
        analysis_data = service.analyze(command.text_content)

        result = SentimentAnalysisResult(
            media_id=command.media_id,
            label=analysis_data.get("label"),
            score=analysis_data.get("score"),
            full_result=analysis_data
        )

        saved_result = await self.repository.save(result)

        if self.event_bus:
            await self.event_bus.publish(SentimentAnalysisCompleted(
                media_id=command.media_id,
                sentiment_result=analysis_data
            ))

        logger.info("sentiment_analysis.completed", media_id=command.media_id)
        return saved_result
