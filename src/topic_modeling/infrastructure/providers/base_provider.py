# src/topic_modeling/infrastructure/providers/base_provider.py
"""
Base implementation for topic modeling providers - Template Method pattern.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
import time

from src.topic_modeling.domain.interfaces import (
    TopicModelingProvider, 
    TopicModelingConfiguration
)


class TopicModelingProviderError(Exception):
    """Base exception for topic modeling provider errors."""
    pass


class BaseTopicModelingProvider(TopicModelingProvider):
    """
    Base topic modeling provider implementing common functionality.
    Follows Template Method pattern and OCP.
    """
    
    def __init__(self, config: TopicModelingConfiguration):
        self._config = config
        self._validate_configuration()
        self._initialize_provider()
    
    def _validate_configuration(self) -> None:
        """Validate provider configuration."""
        if not self._config.validate_config():
            raise TopicModelingProviderError("Invalid topic modeling configuration")
    
    @abstractmethod
    def _initialize_provider(self) -> None:
        """Initialize provider-specific components."""
        pass
    
    async def extract_topics(
        self, 
        text: str, 
        language: str = "en",
        num_topics: int = 5,
        num_words_per_topic: int = 5
    ) -> List[Dict[str, Any]]:
        """Template method for topic extraction."""
        try:
            # Pre-extraction hook
            await self._pre_extract(text, language, num_topics)
            
            # Input validation
            self._validate_input(text, language, num_topics)
            
            # Text preprocessing
            processed_text = await self._preprocess_text(text, language)
            
            # Language validation/detection
            validated_language = await self._validate_and_detect_language(language, processed_text)
            
            # Actual topic extraction (implemented by subclasses)
            raw_topics = await self._do_extract_topics(
                processed_text, validated_language, num_topics, num_words_per_topic
            )
            
            # Post-processing
            structured_topics = await self._postprocess_topics(raw_topics, validated_language)
            
            # Post-extraction hook
            await self._post_extract(text, language, structured_topics)
            
            return structured_topics
            
        except Exception as e:
            await self._handle_extraction_error(text, language, e)
            raise TopicModelingProviderError(f"Topic extraction failed") from e
    
    def _validate_input(self, text: str, language: str, num_topics: int) -> None:
        """Validate input parameters."""
        if not text or not text.strip():
            raise TopicModelingProviderError("Text content is empty")
        
        max_length = self._config.get_max_text_length()
        if len(text) > max_length:
            raise TopicModelingProviderError(
                f"Text length {len(text)} exceeds maximum {max_length}"
            )
        
        if num_topics < 1 or num_topics > 50:
            raise TopicModelingProviderError("Number of topics must be between 1 and 50")
    
    async def get_capabilities(self) -> Dict[str, Any]:
        """Get provider capabilities."""
        return {
            "provider_name": self.provider_name,
            "supported_languages": await self.get_supported_languages(),
            "max_text_length": self._config.get_max_text_length(),
            "supports_multilingual": self._supports_multilingual(),
            "supports_dynamic_topics": self._supports_dynamic_topics(),
            "supports_coherence_scoring": self._supports_coherence_scoring(),
            **await self._get_provider_specific_capabilities()
        }
    
    # Abstract methods to be implemented by subclasses
    @abstractmethod
    async def _do_extract_topics(
        self, 
        text: str, 
        language: str, 
        num_topics: int,
        num_words_per_topic: int
    ) -> List[Dict[str, Any]]:
        """Actual topic extraction implementation."""
        pass
    
    @abstractmethod
    async def get_supported_languages(self) -> List[str]:
        """Get supported languages."""
        pass
    
    @abstractmethod
    def _supports_multilingual(self) -> bool:
        """Whether provider supports multilingual processing."""
        pass
    
    @abstractmethod
    def _supports_dynamic_topics(self) -> bool:
        """Whether provider supports dynamic topic number detection."""
        pass
    
    @abstractmethod
    def _supports_coherence_scoring(self) -> bool:
        """Whether provider supports coherence scoring."""
        pass
    
    # Hook methods (can be overridden by subclasses)
    async def _pre_extract(self, text: str, language: str, num_topics: int) -> None:
        """Hook called before topic extraction."""
        pass
    
    async def _post_extract(
        self, 
        text: str, 
        language: str, 
        topics: List[Dict[str, Any]]
    ) -> None:
        """Hook called after successful topic extraction."""
        pass
    
    async def _preprocess_text(self, text: str, language: str) -> str:
        """Preprocess text for topic modeling."""
        # Default implementation: basic cleaning
        cleaned = text.strip()
        
        # Remove excessive whitespace
        import re
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Remove URLs
        cleaned = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', cleaned)
        
        # Remove email addresses
        cleaned = re.sub(r'\S+@\S+', '', cleaned)
        
        return cleaned.strip()
    
    async def _validate_and_detect_language(self, language: str, text: str) -> str:
        """Validate and potentially detect language."""
        supported_languages = await self.get_supported_languages()
        
        if language == "auto":
            # Try to detect language
            return await self._detect_language(text)
        
        # Validate provided language
        if language not in supported_languages:
            # Fallback to English or first supported language
            return "en" if "en" in supported_languages else supported_languages[0]
        
        return language
    
    async def _detect_language(self, text: str) -> str:
        """Detect language from text (default implementation)."""
        # Simple heuristic - can be overridden by providers
        # Look for common English words
        english_words = ["the", "and", "or", "but", "in", "on", "at", "to", "for", "of"]
        text_lower = text.lower()
        
        english_count = sum(1 for word in english_words if word in text_lower)
        
        if english_count >= 3:
            return "en"
        
        # Default fallback
        supported = await self.get_supported_languages()
        return supported[0] if supported else "en"
    
    async def _postprocess_topics(
        self, 
        raw_topics: List[Dict[str, Any]], 
        language: str
    ) -> List[Dict[str, Any]]:
        """Post-process topics to standard format."""
        structured_topics = []
        
        for i, topic in enumerate(raw_topics):
            structured_topic = {
                "topic_id": i + 1,
                "words": topic.get("words", []),
                "scores": topic.get("scores", []),
                "coherence_score": topic.get("coherence_score", 0.0),
                "dominant_words": topic.get("dominant_words", []),
                "metadata": {
                    "provider": self.provider_name,
                    "language": language,
                    "timestamp": time.time()
                }
            }
            
            # Ensure we have at least the basic structure
            if not structured_topic["words"]:
                continue
            
            structured_topics.append(structured_topic)
        
        return structured_topics
    
    async def _handle_extraction_error(
        self, 
        text: str, 
        language: str, 
        error: Exception
    ) -> None:
        """Handle topic extraction errors."""
        pass
    
    async def _get_provider_specific_capabilities(self) -> Dict[str, Any]:
        """Get provider-specific capabilities."""
        return {}
    
    def _calculate_word_importance(self, word_scores: List[float]) -> List[float]:
        """Calculate normalized word importance scores."""
        if not word_scores:
            return []
        
        max_score = max(word_scores)
        min_score = min(word_scores)
        
        if max_score == min_score:
            return [1.0] * len(word_scores)
        
        # Normalize to 0-1 range
        normalized = [
            (score - min_score) / (max_score - min_score)
            for score in word_scores
        ]
        
        return normalized
    
    def _filter_low_quality_words(
        self, 
        words: List[str], 
        scores: List[float], 
        min_score: float = 0.1
    ) -> tuple[List[str], List[float]]:
        """Filter out low-quality words."""
        if len(words) != len(scores):
            return words, scores
        
        filtered_words = []
        filtered_scores = []
        
        for word, score in zip(words, scores):
            if score >= min_score and len(word) > 2:  # Minimum word length
                filtered_words.append(word)
                filtered_scores.append(score)
        
        return filtered_words, filtered_scores