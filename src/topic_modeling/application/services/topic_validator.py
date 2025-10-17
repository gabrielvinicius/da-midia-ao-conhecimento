# src/topic_modeling/application/services/topic_validator.py
"""
Topic validation service implementation - SRP compliance.
"""
from typing import Dict, Any, List
import math

from src.topic_modeling.domain.interfaces import TopicValidator


class DefaultTopicValidator(TopicValidator):
    """
    Default implementation of topic validation.
    Follows SRP - only responsible for topic validation operations.
    """
    
    def __init__(
        self,
        min_coherence_score: float = 0.1,
        min_words_per_topic: int = 3,
        max_words_per_topic: int = 20,
        min_topic_score: float = 0.01,
        diversity_threshold: float = 0.3
    ):
        self.min_coherence_score = min_coherence_score
        self.min_words_per_topic = min_words_per_topic
        self.max_words_per_topic = max_words_per_topic
        self.min_topic_score = min_topic_score
        self.diversity_threshold = diversity_threshold
    
    async def validate_topics(self, topics: List[Dict[str, Any]]) -> bool:
        """Validate extracted topics."""
        if not topics or not isinstance(topics, list):
            return False
        
        for topic in topics:
            if not await self._validate_single_topic(topic):
                return False
        
        # Check topic diversity
        if not await self._check_topic_diversity(topics):
            return False
        
        return True
    
    async def calculate_coherence_score(self, topics: List[Dict[str, Any]]) -> float:
        """Calculate overall coherence score for topics."""
        if not topics:
            return 0.0
        
        coherence_scores = []
        
        for topic in topics:
            topic_coherence = await self._calculate_single_topic_coherence(topic)
            coherence_scores.append(topic_coherence)
        
        # Return average coherence
        return sum(coherence_scores) / len(coherence_scores)
    
    async def filter_topics(
        self, 
        topics: List[Dict[str, Any]], 
        min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Filter topics by quality score."""
        filtered_topics = []
        
        for topic in topics:
            quality_score = await self._calculate_topic_quality_score(topic)
            
            if quality_score >= min_score:
                # Add quality score to topic metadata
                if "metadata" not in topic:
                    topic["metadata"] = {}
                topic["metadata"]["quality_score"] = quality_score
                
                filtered_topics.append(topic)
        
        # Sort by quality score (highest first)
        filtered_topics.sort(
            key=lambda t: t.get("metadata", {}).get("quality_score", 0),
            reverse=True
        )
        
        return filtered_topics
    
    async def _validate_single_topic(self, topic: Dict[str, Any]) -> bool:
        """Validate a single topic."""
        # Check required fields
        if not isinstance(topic, dict):
            return False
        
        # Check words field
        words = topic.get("words", [])
        if not isinstance(words, list) or len(words) < self.min_words_per_topic:
            return False
        
        # Check word quality
        for word in words:
            if not isinstance(word, str) or len(word.strip()) < 2:
                return False
        
        # Check scores if present
        scores = topic.get("scores", [])
        if scores:
            if len(scores) != len(words):
                return False
            
            # Check score values
            for score in scores:
                if not isinstance(score, (int, float)) or score < 0:
                    return False
        
        # Check coherence score if present
        coherence_score = topic.get("coherence_score", 0.0)
        if coherence_score < 0 or coherence_score > 1:
            return False
        
        return True
    
    async def _check_topic_diversity(self, topics: List[Dict[str, Any]]) -> bool:
        """Check diversity between topics."""
        if len(topics) < 2:
            return True  # Single topic is always diverse
        
        # Calculate word overlap between topics
        topic_words = []
        for topic in topics:
            words = topic.get("words", [])
            topic_words.append(set(word.lower() for word in words))
        
        # Check pairwise diversity
        total_comparisons = 0
        diverse_comparisons = 0
        
        for i in range(len(topic_words)):
            for j in range(i + 1, len(topic_words)):
                total_comparisons += 1
                
                # Calculate Jaccard similarity
                intersection = len(topic_words[i] & topic_words[j])
                union = len(topic_words[i] | topic_words[j])
                
                similarity = intersection / union if union > 0 else 0
                diversity = 1 - similarity
                
                if diversity >= self.diversity_threshold:
                    diverse_comparisons += 1
        
        # At least 70% of topic pairs should be diverse
        diversity_ratio = diverse_comparisons / total_comparisons if total_comparisons > 0 else 1.0
        return diversity_ratio >= 0.7
    
    async def _calculate_single_topic_coherence(self, topic: Dict[str, Any]) -> float:
        """Calculate coherence score for a single topic."""
        # If coherence score is already provided, use it
        coherence_score = topic.get("coherence_score", 0.0)
        if coherence_score > 0:
            return coherence_score
        
        # Calculate based on word scores distribution
        scores = topic.get("scores", [])
        if not scores:
            return 0.5  # Default coherence for topics without scores
        
        # Coherence based on score distribution
        # More even distribution indicates better coherence
        mean_score = sum(scores) / len(scores)
        variance = sum((score - mean_score) ** 2 for score in scores) / len(scores)
        std_dev = math.sqrt(variance)
        
        # Coefficient of variation (lower is better)
        cv = std_dev / mean_score if mean_score > 0 else 1.0
        
        # Convert to coherence score (0-1, higher is better)
        coherence = max(0.0, 1.0 - min(cv, 1.0))
        
        return coherence
    
    async def _calculate_topic_quality_score(self, topic: Dict[str, Any]) -> float:
        """Calculate overall quality score for a topic."""
        score = 0.0
        max_score = 100.0
        
        # Word quality (30 points)
        words = topic.get("words", [])
        if words:
            score += 15.0  # Has words
            
            # Check word length diversity
            word_lengths = [len(word) for word in words]
            if len(set(word_lengths)) > 1:  # Diverse word lengths
                score += 10.0
            
            # Check for meaningful words (not just single characters)
            meaningful_words = [w for w in words if len(w) > 2]
            if len(meaningful_words) == len(words):
                score += 5.0
        
        # Score distribution quality (25 points)
        scores = topic.get("scores", [])
        if scores:
            score += 10.0  # Has scores
            
            # Check score range
            score_range = max(scores) - min(scores)
            if score_range > 0.1:  # Good score differentiation
                score += 10.0
            
            # Check for decreasing scores (good topic structure)
            is_decreasing = all(scores[i] >= scores[i+1] for i in range(len(scores)-1))
            if is_decreasing:
                score += 5.0
        
        # Coherence score (25 points)
        coherence = topic.get("coherence_score", 0.0)
        score += coherence * 25.0
        
        # Dominant words quality (20 points)
        dominant_words = topic.get("dominant_words", [])
        if dominant_words:
            score += 10.0  # Has dominant words
            
            # Check if dominant words are actually in the topic words
            if all(word in words for word in dominant_words):
                score += 10.0
        
        return min(score, max_score) / max_score
    
    def _calculate_word_uniqueness(self, word: str, all_topic_words: List[List[str]]) -> float:
        """Calculate how unique a word is across all topics."""
        occurrences = sum(1 for topic_words in all_topic_words if word in topic_words)
        total_topics = len(all_topic_words)
        
        # Inverse frequency - more unique words have higher scores
        uniqueness = 1.0 - (occurrences / total_topics) if total_topics > 0 else 1.0
        
        return uniqueness
    
    def _calculate_semantic_coherence(self, words: List[str]) -> float:
        """Calculate semantic coherence between words (simplified)."""
        # Simplified semantic coherence based on word relationships
        # In a real implementation, this could use word embeddings
        
        if len(words) < 2:
            return 1.0
        
        # Simple heuristic: check for word prefix/suffix similarities
        coherence_score = 0.0
        comparisons = 0
        
        for i in range(len(words)):
            for j in range(i + 1, len(words)):
                word1, word2 = words[i].lower(), words[j].lower()
                
                # Check for common prefixes or suffixes
                similarity = self._calculate_word_similarity(word1, word2)
                coherence_score += similarity
                comparisons += 1
        
        return coherence_score / comparisons if comparisons > 0 else 0.0
    
    def _calculate_word_similarity(self, word1: str, word2: str) -> float:
        """Calculate similarity between two words."""
        # Simple similarity based on common characters
        if not word1 or not word2:
            return 0.0
        
        # Jaccard similarity of character sets
        set1, set2 = set(word1), set(word2)
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0