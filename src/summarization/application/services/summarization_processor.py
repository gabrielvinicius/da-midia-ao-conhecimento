# src/summarization/application/services/summarization_processor.py
"""
Summarization Processing Service - Single Responsibility Principle
Extracted from BaseSummarizationTemplate God Class (514 lines)
Handles core text summarization processing operations
"""

import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.summarization.infrastructure.templates.summarization_templates import (
    SummarizationInput, SummaryType, SummaryLength
)
from src.summarization.domain.summary import Summary
from src.shared.infrastructure.logging_config import get_logger

logger = get_logger("summarization_processor")


class SummarizationProcessor:
    """
    Summarization processing with Single Responsibility:
    Execute text summarization operations and content processing
    """
    
    def __init__(self, provider_name: str = "default", model_name: str = "default"):
        self.provider_name = provider_name
        self.model_name = model_name
        self.session_id: Optional[str] = None
        self.processed_text: Optional[str] = None
        self.text_chunks: List[str] = []
        
        # Processing cache for performance
        self.processing_cache = {}
        self.cache_enabled = True
        
    async def process_summarization(
        self, 
        input_data: SummarizationInput, 
        options: Dict[str, Any] = None
    ) -> Summary:
        """
        Main summarization processing entry point
        Returns complete summary result
        """
        options = options or {}
        
        try:
            # Initialize processing session
            await self._initialize_processing(input_data, options)
            
            # Preprocess text
            self.processed_text = await self._preprocess_text(input_data.text, options)
            
            # Chunk text if needed
            self.text_chunks = await self._chunk_text(self.processed_text, input_data, options)
            
            # Generate summary based on type
            if input_data.summary_type == SummaryType.EXTRACTIVE:
                summary_text = await self._generate_extractive_summary(input_data, options)
            elif input_data.summary_type == SummaryType.ABSTRACTIVE:
                summary_text = await self._generate_abstractive_summary(input_data, options)
            elif input_data.summary_type == SummaryType.BULLET_POINTS:
                summary_text = await self._generate_bullet_points(input_data, options)
            elif input_data.summary_type == SummaryType.HEADLINE:
                summary_text = await self._generate_headline(input_data, options)
            else:
                raise ValueError(f"Unsupported summary type: {input_data.summary_type}")
            
            # Post-process summary
            final_summary_text = await self._post_process_summary(summary_text, input_data, options)
            
            # Create Summary object
            summary = Summary(
                text=final_summary_text,
                original_text=input_data.text,
                summary_type=input_data.summary_type,
                language=input_data.language
            )
            
            logger.info(f"Summarization completed: {input_data.summary_type.value}")
            return summary
            
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            raise
    
    async def _generate_extractive_summary(self, input_data: SummarizationInput, options: Dict[str, Any]) -> str:
        """Generate extractive summary by selecting key sentences"""
        
        sentences = self._split_into_sentences(self.processed_text)
        if not sentences:
            return "No content available for summarization."
        
        # Score sentences based on simple heuristics
        sentence_scores = []
        
        for i, sentence in enumerate(sentences):
            score = self._calculate_sentence_importance(sentence, self.processed_text)
            sentence_scores.append((score, i, sentence))
        
        # Sort by score and select top sentences
        sentence_scores.sort(reverse=True)
        target_count = self._get_target_sentence_count(input_data.summary_length)
        target_count = min(target_count, len(sentences))
        
        selected_sentences = sentence_scores[:target_count]
        # Sort selected sentences by original order
        selected_sentences.sort(key=lambda x: x[1])
        
        summary_text = ' '.join([sentence[2] for sentence in selected_sentences])
        return summary_text
    
    async def _generate_abstractive_summary(self, input_data: SummarizationInput, options: Dict[str, Any]) -> str:
        """Generate abstractive summary (mock implementation)"""
        
        # Mock implementation - in production would use actual ML model
        sentences = self._split_into_sentences(self.processed_text)
        
        if not sentences:
            return "No content available for summarization."
        
        # Simple abstractive approach: combine key phrases
        key_phrases = self._extract_key_phrases(self.processed_text)
        
        if input_data.summary_length == SummaryLength.SHORT:
            return f"This text discusses {', '.join(key_phrases[:3])}."
        elif input_data.summary_length == SummaryLength.MEDIUM:
            return f"The main topics covered include {', '.join(key_phrases[:5])}. {sentences[0] if sentences else ''}"
        else:  # LONG or CUSTOM
            summary_parts = [
                f"This content primarily focuses on {', '.join(key_phrases[:3])}.",
                f"Key points include {', '.join(key_phrases[3:6])}." if len(key_phrases) > 3 else "",
                sentences[0] if sentences else ""
            ]
            return ' '.join([part for part in summary_parts if part])
    
    def _calculate_sentence_importance(self, sentence: str, full_text: str) -> float:
        """Calculate importance score for a sentence"""
        
        score = 0.0
        sentence_words = set(sentence.lower().split())
        full_text_words = full_text.lower().split()
        
        # Word frequency score
        word_freq_score = 0
        for word in sentence_words:
            if len(word) > 3:  # Skip short words
                frequency = full_text_words.count(word)
                word_freq_score += frequency
        
        score += word_freq_score / max(len(sentence_words), 1)
        
        # Position score (earlier sentences get slight boost)
        # This would need the sentence position in the full text
        
        # Length score (prefer medium-length sentences)
        word_count = len(sentence_words)
        if 10 <= word_count <= 25:
            score += 0.5
        elif word_count < 5:
            score -= 0.3
        
        return score


# Default instance
summarization_processor = SummarizationProcessor()