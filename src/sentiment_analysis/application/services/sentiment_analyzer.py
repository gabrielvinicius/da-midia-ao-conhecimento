# src/sentiment_analysis/application/services/sentiment_analyzer.py
"""
Sentiment Analysis Core Service - Single Responsibility Principle
Extracted from BaseSentimentAnalysisTemplate God Class (517 lines)
Handles core sentiment analysis processing and text analysis
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from src.sentiment_analysis.infrastructure.templates.sentiment_templates import (
    SentimentInput, SentimentLabel, AnalysisGranularity
)
from src.sentiment_analysis.domain.sentiment_analysis import SentimentAnalysis
from src.shared.infrastructure.logging_config import get_logger

logger = get_logger("sentiment_analyzer")


class SentimentAnalyzer:
    """
    Sentiment analysis with Single Responsibility:
    Execute sentiment analysis operations and text processing
    """
    
    def __init__(self, provider_name: str = "default", model_name: str = "default"):
        self.provider_name = provider_name
        self.model_name = model_name
        self.session_id: Optional[str] = None
        self.processed_text: Optional[str] = None
        self.text_segments: List[str] = []
        
        # Analysis cache for performance
        self.analysis_cache = {}
        self.cache_enabled = True
        
    async def analyze_sentiment(
        self, 
        input_data: SentimentInput, 
        options: Dict[str, Any] = None
    ) -> SentimentAnalysis:
        """
        Main sentiment analysis entry point
        Returns complete sentiment analysis result
        """
        options = options or {}
        
        try:
            # Initialize analysis session
            await self._initialize_analysis(input_data, options)
            
            # Preprocess text
            self.processed_text = await self._preprocess_text(input_data.text, options)
            
            # Segment text based on granularity
            self.text_segments = await self._segment_text(self.processed_text, input_data, options)
            
            # Perform sentiment analysis based on granularity
            if input_data.granularity == AnalysisGranularity.DOCUMENT:
                result = await self._analyze_document_sentiment(input_data, options)
            elif input_data.granularity == AnalysisGranularity.SENTENCE:
                result = await self._analyze_sentence_sentiment(input_data, options)
            elif input_data.granularity == AnalysisGranularity.ASPECT:
                result = await self._analyze_aspect_sentiment(input_data, options)
            else:
                raise ValueError(f"Unsupported granularity: {input_data.granularity}")
            
            # Post-process results
            final_result = await self._post_process_results(result, input_data, options)
            
            logger.info(f"Sentiment analysis completed: {input_data.granularity.value}")
            return final_result
            
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            raise
    
    def _calculate_sentiment_scores(self, text: str) -> Dict[str, float]:
        """
        Calculate sentiment scores for text
        Mock implementation - in production would use actual ML model
        """
        
        # Simple keyword-based sentiment scoring (for demonstration)
        positive_words = [
            "good", "great", "excellent", "amazing", "wonderful", "fantastic",
            "love", "like", "enjoy", "happy", "pleased", "satisfied", "perfect"
        ]
        
        negative_words = [
            "bad", "terrible", "awful", "horrible", "hate", "dislike",
            "angry", "frustrated", "disappointed", "sad", "annoyed", "upset"
        ]
        
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        
        positive_count = sum(1 for word in words if word in positive_words)
        negative_count = sum(1 for word in words if word in negative_words)
        
        total_words = max(len(words), 1)
        
        # Calculate scores
        positive_score = positive_count / total_words
        negative_score = negative_count / total_words
        neutral_score = max(0.1, 1.0 - positive_score - negative_score)
        
        # Normalize scores
        total_score = positive_score + negative_score + neutral_score
        if total_score > 0:
            positive_score /= total_score
            negative_score /= total_score
            neutral_score /= total_score
        
        return {
            "positive": round(positive_score, 3),
            "negative": round(negative_score, 3),
            "neutral": round(neutral_score, 3)
        }


# Default instance
sentiment_analyzer = SentimentAnalyzer()