# src/topic_modeling/application/services/topic_modeling_state_manager.py
"""
Topic modeling state management service - SRP compliance.
"""
from typing import Optional, Dict, Any, List
import structlog
from uuid import uuid4

from src.topic_modeling.domain.interfaces import TopicModelingStateManager, ITopicModelingRepository
from src.topic_modeling.domain.topic_modeling import TopicModelingResult

logger = structlog.get_logger(__name__)


class TopicModelingStateManagerImpl(TopicModelingStateManager):
    """
    Implementation of topic modeling state management.
    Follows SRP - only responsible for state transitions.
    """
    
    def __init__(self, repository: ITopicModelingRepository):
        self._repository = repository
    
    async def start_processing(
        self, 
        media_id: str, 
        provider: str,
        language: str
    ) -> TopicModelingResult:
        """Start processing and return result."""
        logger.info(
            "topic_modeling.state.start_processing",
            media_id=media_id,
            provider=provider,
            language=language
        )
        
        # Check if result already exists
        from uuid import UUID
        existing_result = await self._repository.find_by_media_id(UUID(media_id))
        
        if existing_result:
            # Update existing result for reprocessing
            existing_result.topics = {}  # Clear previous topics
            result = await self._repository.save(existing_result)
            
            logger.info(
                "topic_modeling.state.restarted_existing",
                result_id=str(result.id),
                media_id=media_id
            )
        else:
            # Create new result
            result = TopicModelingResult(
                id=uuid4(),
                media_id=UUID(media_id),
                topics={}  # Will be populated when processing completes
            )
            result = await self._repository.save(result)
            
            logger.info(
                "topic_modeling.state.created_new",
                result_id=str(result.id),
                media_id=media_id
            )
        
        return result
    
    async def complete_processing(
        self, 
        result: TopicModelingResult, 
        topics: List[Dict[str, Any]]
    ) -> TopicModelingResult:
        """Complete processing with topics."""
        logger.info(
            "topic_modeling.state.complete_processing",
            result_id=str(result.id),
            num_topics=len(topics)
        )
        
        # Structure the topics data
        structured_topics = {
            "topics": topics,
            "num_topics": len(topics),
            "extraction_metadata": {
                "timestamp": TopicModelingResult._get_current_timestamp(),
                "success": True
            }
        }
        
        # Calculate overall statistics
        if topics:
            coherence_scores = [topic.get("coherence_score", 0.0) for topic in topics]
            structured_topics["extraction_metadata"]["avg_coherence"] = (
                sum(coherence_scores) / len(coherence_scores)
            )
            
            # Extract top words across all topics
            all_words = []
            for topic in topics:
                words = topic.get("words", [])
                all_words.extend(words[:3])  # Top 3 words from each topic
            
            structured_topics["extraction_metadata"]["top_words"] = list(set(all_words))
        
        # Update result
        result.topics = structured_topics
        updated_result = await self._repository.save(result)
        
        logger.info(
            "topic_modeling.state.completed",
            result_id=str(updated_result.id),
            num_topics=len(topics)
        )
        
        return updated_result
    
    async def fail_processing(
        self, 
        result: TopicModelingResult, 
        error: str
    ) -> TopicModelingResult:
        """Mark processing as failed."""
        logger.info(
            "topic_modeling.state.fail_processing",
            result_id=str(result.id),
            error=error
        )
        
        # Truncate error message if too long
        truncated_error = error[:500] if len(error) > 500 else error
        
        # Update result with error information
        failed_topics = {
            "topics": [],
            "num_topics": 0,
            "extraction_metadata": {
                "timestamp": TopicModelingResult._get_current_timestamp(),
                "success": False,
                "error": truncated_error
            }
        }
        
        result.topics = failed_topics
        updated_result = await self._repository.save(result)
        
        logger.error(
            "topic_modeling.state.failed",
            result_id=str(updated_result.id),
            error=truncated_error
        )
        
        return updated_result
    
    async def get_result_state(self, media_id: str) -> Optional[TopicModelingResult]:
        """Get current result state for media."""
        from uuid import UUID
        return await self._repository.find_by_media_id(UUID(media_id))
    
    async def is_processing(self, media_id: str) -> bool:
        """Check if topic modeling is currently processing."""
        result = await self.get_result_state(media_id)
        if not result:
            return False
        
        # Check if result has topics or error
        topics_data = result.topics or {}
        metadata = topics_data.get("extraction_metadata", {})
        
        # If no metadata, assume it's still processing
        return "success" not in metadata
    
    async def reset_failed_result(self, media_id: str) -> Optional[TopicModelingResult]:
        """Reset a failed result to allow reprocessing."""
        result = await self.get_result_state(media_id)
        
        if result:
            topics_data = result.topics or {}
            metadata = topics_data.get("extraction_metadata", {})
            
            # Only reset if it was actually failed
            if metadata.get("success") is False:
                result.topics = {}  # Clear topics for reprocessing
                updated_result = await self._repository.save(result)
                
                logger.info(
                    "topic_modeling.state.reset",
                    result_id=str(updated_result.id),
                    media_id=media_id
                )
                
                return updated_result
        
        return None
    
    async def get_processing_status(self, media_id: str) -> str:
        """Get processing status for media."""
        result = await self.get_result_state(media_id)
        
        if not result:
            return "not_started"
        
        topics_data = result.topics or {}
        metadata = topics_data.get("extraction_metadata", {})
        
        if "success" not in metadata:
            return "processing"
        elif metadata["success"]:
            return "completed"
        else:
            return "failed"
    
    async def get_result_summary(self, media_id: str) -> Optional[Dict[str, Any]]:
        """Get summary of topic modeling result."""
        result = await self.get_result_state(media_id)
        
        if not result:
            return None
        
        topics_data = result.topics or {}
        metadata = topics_data.get("extraction_metadata", {})
        topics = topics_data.get("topics", [])
        
        summary = {
            "media_id": media_id,
            "result_id": str(result.id),
            "status": "completed" if metadata.get("success") else "failed",
            "num_topics": len(topics),
            "created_at": result.created_at.isoformat() if result.created_at else None
        }
        
        if metadata.get("success"):
            summary.update({
                "avg_coherence": metadata.get("avg_coherence", 0.0),
                "top_words": metadata.get("top_words", []),
                "extraction_timestamp": metadata.get("timestamp")
            })
        else:
            summary["error"] = metadata.get("error", "Unknown error")
        
        return summary