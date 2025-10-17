# src/topic_modeling/domain/services/topic_modeling_coordinator.py
"""
Domain service for coordinating topic modeling operations - SRP compliance.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List

from src.topic_modeling.domain.interfaces import (
    TopicModelingProvider,
    TextPreprocessor,
    TopicValidator,
    TopicModelingOperationLogger,
    TopicModelingMetrics,
    TopicModelingNotificationService
)


class TopicModelingOperationError(Exception):
    """Domain exception for topic modeling operation errors."""
    pass


class TopicModelingCoordinator:
    """
    Domain service that coordinates topic modeling operations with logging and metrics.
    Follows SRP by focusing only on coordination logic.
    """
    
    def __init__(
        self,
        provider: TopicModelingProvider,
        preprocessor: TextPreprocessor,
        validator: TopicValidator,
        logger: TopicModelingOperationLogger,
        metrics: TopicModelingMetrics,
        notification_service: TopicModelingNotificationService
    ):
        self._provider = provider
        self._preprocessor = preprocessor
        self._validator = validator
        self._logger = logger
        self._metrics = metrics
        self._notification_service = notification_service
    
    async def extract_topics_from_text(
        self, 
        media_id: str,
        text_content: str,
        language: str,
        user_id: str,
        num_topics: int = 5
    ) -> List[Dict[str, Any]]:
        """Extract topics with complete workflow coordination."""
        start_time = datetime.utcnow()
        success = False
        error = None
        text_length = len(text_content)
        extracted_topics = []
        coherence_score = 0.0
        
        try:
            # Notify processing started
            await self._notification_service.notify_started(media_id, user_id, self._provider.provider_name)
            
            # Validate and preprocess text
            if not await self._preprocessor.validate_text(text_content):
                raise TopicModelingOperationError("Invalid text content for topic modeling")
            
            # Get text statistics
            text_stats = await self._preprocessor.get_text_stats(text_content)
            
            # Preprocess text
            processed_text = await self._preprocessor.preprocess_text(text_content, language)
            
            # Validate language support
            supported_languages = await self._provider.get_supported_languages()
            if language not in supported_languages and language != "auto":
                # Try to fall back to a supported language
                language = "en" if "en" in supported_languages else supported_languages[0]
            
            # Extract topics
            raw_topics = await self._provider.extract_topics(
                text=processed_text,
                language=language,
                num_topics=num_topics,
                num_words_per_topic=5
            )
            
            # Validate extracted topics
            if not await self._validator.validate_topics(raw_topics):
                raise TopicModelingOperationError("Invalid topics extracted")
            
            # Calculate coherence score
            coherence_score = await self._validator.calculate_coherence_score(raw_topics)
            
            # Filter topics by quality
            filtered_topics = await self._validator.filter_topics(raw_topics, min_score=0.1)
            
            extracted_topics = filtered_topics
            
            # Notify completion
            await self._notification_service.notify_completed(media_id, user_id, extracted_topics)
            
            success = True
            return extracted_topics
            
        except Exception as e:
            error = e
            success = False
            
            # Notify failure
            await self._notification_service.notify_failed(media_id, user_id, str(e))
            
            raise TopicModelingOperationError(
                f"Failed to extract topics for media {media_id}: {e}"
            ) from e
            
        finally:
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            # Log operation
            await self._logger.log_operation(
                operation="extract_topics",
                media_id=media_id,
                provider=self._provider.provider_name,
                language=language,
                success=success,
                duration=duration,
                num_topics=len(extracted_topics),
                text_length=text_length,
                error=error
            )
            
            # Record metrics
            await self._metrics.record_operation(
                operation="extract_topics",
                provider=self._provider.provider_name,
                language=language,
                duration=duration,
                success=success,
                text_length=text_length,
                num_topics=len(extracted_topics),
                coherence_score=coherence_score
            )
    
    async def analyze_text_quality(self, text_content: str) -> Dict[str, Any]:
        """Analyze text quality for topic modeling."""
        try:
            # Get text statistics
            stats = await self._preprocessor.get_text_stats(text_content)
            
            # Validate text
            is_valid = await self._preprocessor.validate_text(text_content)
            
            return {
                "is_valid": is_valid,
                "stats": stats,
                "recommendation": self._get_modeling_recommendation(stats)
            }
        except Exception as e:
            return {
                "is_valid": False,
                "stats": {},
                "recommendation": f"Error analyzing text: {e}"
            }
    
    async def get_provider_capabilities(self) -> Dict[str, Any]:
        """Get current provider capabilities."""
        try:
            return await self._provider.get_capabilities()
        except Exception:
            return {"provider_name": self._provider.provider_name}
    
    def _get_modeling_recommendation(self, stats: Dict[str, Any]) -> str:
        """Get recommendation based on text statistics."""
        word_count = stats.get("word_count", 0)
        
        if word_count < 50:
            return "Text too short for reliable topic modeling. Minimum 50 words recommended."
        elif word_count < 200:
            return "Text is short. Topic modeling may produce limited results."
        elif word_count < 1000:
            return "Text length is adequate for topic modeling."
        else:
            return "Text length is excellent for detailed topic modeling."