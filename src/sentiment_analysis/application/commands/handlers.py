"""
Sentiment Analysis Command Handlers - Pure execution logic following Command Pattern
"""
import structlog
from typing import Dict, Any

from src.sentiment_analysis.domain.interfaces import SentimentAnalysisOrchestrator
from .commands import (
    AnalyzeSentimentCommand,
    ProcessSentimentAnalysisCommand
)

logger = structlog.get_logger(__name__)


class AnalyzeSentimentCommandHandler:
    """Handler for analyze sentiment command"""
    
    def __init__(self, orchestrator: SentimentAnalysisOrchestrator):
        self.orchestrator = orchestrator

    async def handle(self, command: AnalyzeSentimentCommand) -> Dict[str, Any]:
        """Execute sentiment analysis command"""
        logger.info(
            "sentiment.analyze.started",
            media_id=command.media_id,
            provider=command.provider,
            text_length=len(command.text_content)
        )
        
        try:
            analysis = await self.orchestrator.analyze_sentiment(
                text_content=command.text_content,
                media_id=command.media_id,
                provider=command.provider,
                language=command.language
            )
            
            logger.info(
                "sentiment.analyze.completed",
                media_id=command.media_id,
                analysis_id=str(analysis.id),
                sentiment=analysis.overall_sentiment
            )
            
            return {
                "success": True,
                "analysis": {
                    "id": str(analysis.id),
                    "media_id": command.media_id,
                    "overall_sentiment": analysis.overall_sentiment,
                    "confidence": analysis.confidence,
                    "provider": command.provider
                },
                "message": "Sentiment analysis completed successfully"
            }
            
        except Exception as e:
            logger.error(
                "sentiment.analyze.failed",
                media_id=command.media_id,
                error=str(e)
            )
            return {
                "success": False,
                "error": str(e),
                "message": f"Sentiment analysis failed: {str(e)}"
            }


class ProcessSentimentAnalysisCommandHandler:
    """Handler for process sentiment analysis command"""
    
    def __init__(self, orchestrator: SentimentAnalysisOrchestrator):
        self.orchestrator = orchestrator

    async def handle(self, command: ProcessSentimentAnalysisCommand) -> Dict[str, Any]:
        """Execute sentiment analysis processing command"""
        logger.info(
            "sentiment.process.started",
            media_id=command.media_id,
            transcription_id=command.transcription_id,
            provider=command.provider
        )
        
        try:
            analysis = await self.orchestrator.process_sentiment_analysis(
                media_id=command.media_id,
                transcription_id=command.transcription_id,
                provider=command.provider,
                analysis_options=command.analysis_options or {}
            )
            
            logger.info(
                "sentiment.process.completed",
                media_id=command.media_id,
                analysis_id=str(analysis.id) if analysis else None
            )
            
            return {
                "success": True,
                "analysis": {
                    "id": str(analysis.id),
                    "media_id": command.media_id,
                    "transcription_id": command.transcription_id,
                    "provider": command.provider
                } if analysis else None,
                "message": "Sentiment analysis processing completed successfully"
            }
            
        except Exception as e:
            logger.error(
                "sentiment.process.failed",
                media_id=command.media_id,
                error=str(e)
            )
            return {
                "success": False,
                "error": str(e),
                "message": f"Sentiment analysis processing failed: {str(e)}"
            }