# src/topic_modeling/application/services/topic_modeling_orchestrator.py
"""
Topic modeling orchestrator implementation - DIP compliance.
"""
from typing import Optional, Dict, Any
import structlog

from src.topic_modeling.domain.interfaces import (
    TopicModelingOrchestrator,
    ITopicModelingRepository,
    TopicModelingStateManager
)
from src.topic_modeling.domain.topic_modeling import TopicModelingResult
from src.topic_modeling.domain.services.topic_modeling_coordinator import TopicModelingCoordinator

logger = structlog.get_logger(__name__)


class TopicModelingOrchestratorImpl(TopicModelingOrchestrator):
    """
    High-level orchestrator for topic modeling operations.
    Follows DIP - depends on abstractions, not concretions.
    """
    
    def __init__(
        self,
        repository: ITopicModelingRepository,
        state_manager: TopicModelingStateManager,
        coordinator: TopicModelingCoordinator
    ):
        self._repository = repository
        self._state_manager = state_manager
        self._coordinator = coordinator
    
    async def process_topic_modeling(
        self, 
        media_id: str, 
        text_content: str,
        language: str,
        provider: str,
        user_id: str,
        num_topics: int = 5
    ) -> TopicModelingResult:
        """Process complete topic modeling workflow."""
        logger.info(
            "topic_modeling.orchestrator.start",
            media_id=media_id,
            language=language,
            provider=provider,
            user_id=user_id,
            num_topics=num_topics,
            text_length=len(text_content)
        )
        
        # Check if already processing
        if await self._state_manager.is_processing(media_id):
            existing_result = await self._state_manager.get_result_state(media_id)
            logger.warning(
                "topic_modeling.orchestrator.already_processing",
                media_id=media_id,
                result_id=str(existing_result.id) if existing_result else None
            )
            return existing_result
        
        result = None
        try:
            # 1. Start processing
            result = await self._state_manager.start_processing(
                media_id=media_id,
                provider=provider,
                language=language
            )
            
            # 2. Perform topic modeling through coordinator
            topics = await self._coordinator.extract_topics_from_text(
                media_id=media_id,
                text_content=text_content,
                language=language,
                user_id=user_id,
                num_topics=num_topics
            )
            
            # 3. Complete processing
            result = await self._state_manager.complete_processing(
                result=result,
                topics=topics
            )
            
            logger.info(
                "topic_modeling.orchestrator.completed",
                media_id=media_id,
                result_id=str(result.id),
                num_topics=len(topics)
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "topic_modeling.orchestrator.failed",
                media_id=media_id,
                error=str(e),
                result_id=str(result.id) if result else None
            )
            
            # Handle failure
            if result:
                result = await self._state_manager.fail_processing(
                    result=result,
                    error=str(e)
                )
            
            raise
    
    async def get_topics(self, media_id: str) -> Optional[TopicModelingResult]:
        """Get existing topic modeling result."""
        return await self._state_manager.get_result_state(media_id)
    
    async def retry_failed_modeling(
        self, 
        media_id: str, 
        text_content: str,
        language: str,
        provider: str,
        user_id: str,
        num_topics: int = 5
    ) -> TopicModelingResult:
        """Retry failed topic modeling."""
        logger.info(
            "topic_modeling.orchestrator.retry",
            media_id=media_id,
            provider=provider
        )
        
        # Reset failed result
        await self._state_manager.reset_failed_result(media_id)
        
        # Process again
        return await self.process_topic_modeling(
            media_id=media_id,
            text_content=text_content,
            language=language,
            provider=provider,
            user_id=user_id,
            num_topics=num_topics
        )
    
    async def get_processing_status(self, media_id: str) -> str:
        """Get current processing status."""
        return await self._state_manager.get_processing_status(media_id)
    
    async def delete_topics(self, media_id: str) -> bool:
        """Delete topic modeling result for media."""
        logger.info("topic_modeling.orchestrator.delete", media_id=media_id)
        
        result = await self._state_manager.get_result_state(media_id)
        if result:
            return await self._repository.delete(result.id)
        
        return False
    
    async def get_result_summary(self, media_id: str) -> Optional[Dict[str, Any]]:
        """Get summary of topic modeling result."""
        return await self._state_manager.get_result_summary(media_id)
    
    async def analyze_text_quality(self, text_content: str) -> Dict[str, Any]:
        """Analyze text quality for topic modeling."""
        try:
            return await self._coordinator.analyze_text_quality(text_content)
        except Exception as e:
            logger.error(
                "topic_modeling.orchestrator.text_analysis_failed",
                error=str(e)
            )
            return {
                "is_valid": False,
                "stats": {},
                "recommendation": f"Error analyzing text: {e}"
            }
    
    async def get_provider_capabilities(self) -> Dict[str, Any]:
        """Get current provider capabilities."""
        try:
            return await self._coordinator.get_provider_capabilities()
        except Exception:
            return {"error": "Unable to get provider capabilities"}
    
    async def extract_topics_with_options(
        self,
        media_id: str,
        text_content: str,
        options: Dict[str, Any],
        user_id: str
    ) -> TopicModelingResult:
        """Extract topics with custom options."""
        # Extract options
        language = options.get("language", "en")
        provider = options.get("provider", "sklearn_lda")
        num_topics = options.get("num_topics", 5)
        
        # Validate options
        if num_topics < 1 or num_topics > 50:
            raise ValueError("Number of topics must be between 1 and 50")
        
        return await self.process_topic_modeling(
            media_id=media_id,
            text_content=text_content,
            language=language,
            provider=provider,
            user_id=user_id,
            num_topics=num_topics
        )
    
    async def get_topic_details(self, media_id: str, topic_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific topic."""
        result = await self.get_topics(media_id)
        
        if not result or not result.topics:
            return None
        
        topics = result.topics.get("topics", [])
        
        # Find topic by ID (1-based)
        if 1 <= topic_id <= len(topics):
            topic = topics[topic_id - 1]
            
            # Add additional details
            detailed_topic = {
                **topic,
                "topic_id": topic_id,
                "total_topics": len(topics),
                "relative_importance": topic_id / len(topics)
            }
            
            return detailed_topic
        
        return None