"""
Topic Modeling Command Handlers - Pure execution logic following Command Pattern
"""
import structlog
from typing import Dict, Any

from src.topic_modeling.domain.interfaces import TopicModelingOrchestrator
from .commands import (
    ProcessTopicModelingCommand,
    AnalyzeTopicsCommand
)

logger = structlog.get_logger(__name__)


class ProcessTopicModelingCommandHandler:
    """Handler for process topic modeling command"""
    
    def __init__(self, orchestrator: TopicModelingOrchestrator):
        self.orchestrator = orchestrator

    async def handle(self, command: ProcessTopicModelingCommand) -> Dict[str, Any]:
        """Execute topic modeling processing command"""
        logger.info(
            "topic_modeling.process.started",
            media_id=command.media_id,
            provider=command.provider,
            num_topics=command.num_topics
        )
        
        try:
            analysis = await self.orchestrator.process_topic_modeling(
                media_id=command.media_id,
                text_content=command.text_content,
                provider=command.provider,
                num_topics=command.num_topics
            )
            
            logger.info(
                "topic_modeling.process.completed",
                media_id=command.media_id,
                analysis_id=str(analysis.id),
                topics_found=len(analysis.topics) if analysis.topics else 0
            )
            
            return {
                "success": True,
                "analysis": {
                    "id": str(analysis.id),
                    "media_id": command.media_id,
                    "topics": analysis.topics,
                    "num_topics": command.num_topics,
                    "provider": command.provider
                },
                "message": "Topic modeling completed successfully"
            }
            
        except Exception as e:
            logger.error(
                "topic_modeling.process.failed",
                media_id=command.media_id,
                error=str(e)
            )
            return {
                "success": False,
                "error": str(e),
                "message": f"Topic modeling failed: {str(e)}"
            }


class AnalyzeTopicsCommandHandler:
    """Handler for analyze topics command"""
    
    def __init__(self, orchestrator: TopicModelingOrchestrator):
        self.orchestrator = orchestrator

    async def handle(self, command: AnalyzeTopicsCommand) -> Dict[str, Any]:
        """Execute topics analysis command"""
        logger.info(
            "topic_modeling.analyze.started",
            transcription_id=command.transcription_id,
            provider=command.provider
        )
        
        try:
            analysis = await self.orchestrator.analyze_topics(
                transcription_id=command.transcription_id,
                provider=command.provider,
                modeling_options=command.modeling_options or {}
            )
            
            logger.info(
                "topic_modeling.analyze.completed",
                transcription_id=command.transcription_id,
                analysis_id=str(analysis.id) if analysis else None
            )
            
            return {
                "success": True,
                "analysis": {
                    "id": str(analysis.id),
                    "transcription_id": command.transcription_id,
                    "provider": command.provider
                } if analysis else None,
                "message": "Topics analysis completed successfully"
            }
            
        except Exception as e:
            logger.error(
                "topic_modeling.analyze.failed",
                transcription_id=command.transcription_id,
                error=str(e)
            )
            return {
                "success": False,
                "error": str(e),
                "message": f"Topics analysis failed: {str(e)}"
            }