# src/sentiment_analysis/application/services/sentiment_validator.py
"""
Sentiment Analysis Validation Service - Single Responsibility Principle
Extracted from BaseSentimentAnalysisTemplate God Class (517 lines)
Handles all sentiment analysis input validation and constraint checking
"""

import re
from typing import Dict, Any, List, Optional
from enum import Enum

from src.sentiment_analysis.infrastructure.templates.sentiment_templates import SentimentInput, AnalysisGranularity
from src.shared.infrastructure.logging_config import get_logger

logger = get_logger("sentiment_validator")


class SentimentValidator:
    """
    Sentiment validation with Single Responsibility:
    Validate text inputs, language support, and analysis constraints
    """
    
    def __init__(self):
        self.supported_languages = [
            "en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja", "ko"
        ]
        self.supported_granularities = list(AnalysisGranularity)
        self.text_limits = {
            "min_length": 3,
            "max_length": 500000,
            "max_aspects": 20,
            "min_aspect_length": 2
        }
    
    async def validate_input(
        self, 
        input_data: SentimentInput, 
        options: Dict[str, Any] = None
    ) -> tuple[bool, List[str]]:
        """
        Validate sentiment analysis input
        Returns: (is_valid, error_messages)
        """
        errors = []
        options = options or {}
        
        # Validate text content
        text_errors = await self._validate_text_content(input_data, options)
        errors.extend(text_errors)
        
        # Validate language support
        language_errors = await self._validate_language_support(input_data)
        errors.extend(language_errors)
        
        # Validate analysis configuration
        config_errors = await self._validate_analysis_config(input_data)
        errors.extend(config_errors)
        
        # Validate aspects if specified
        if input_data.aspects:
            aspect_errors = await self._validate_aspects(input_data)
            errors.extend(aspect_errors)
        
        # Validate additional constraints
        constraint_errors = await self._validate_constraints(input_data, options)
        errors.extend(constraint_errors)
        
        is_valid = len(errors) == 0
        
        if is_valid:
            logger.info(f"Sentiment input validation passed: {input_data.language}/{input_data.granularity.value}")
        else:
            logger.warning(f"Sentiment input validation failed: {len(errors)} errors")
            for error in errors:
                logger.warning(f"  - {error}")
        
        return is_valid, errors
    
    async def _validate_text_content(self, input_data: SentimentInput, options: Dict[str, Any]) -> List[str]:
        """Validate text content and length"""
        errors = []
        
        # Check if text exists
        if not input_data.text:
            errors.append("Text content is missing")
            return errors
        
        # Check if text is not empty after stripping
        text_stripped = input_data.text.strip()
        if len(text_stripped) == 0:
            errors.append("Text content is empty")
            return errors
        
        # Check text length limits
        min_length = options.get("min_text_length", self.text_limits["min_length"])
        max_length = options.get("max_text_length", self.text_limits["max_length"])
        
        text_length = len(input_data.text)
        
        if text_length < min_length:
            errors.append(
                f"Text too short: {text_length} characters (minimum: {min_length})"
            )
        
        if text_length > max_length:
            errors.append(
                f"Text too long: {text_length} characters (maximum: {max_length})"
            )
        
        # Check for potentially problematic content
        if self._contains_only_special_chars(input_data.text):
            errors.append("Text contains only special characters or whitespace")
        
        return errors
    
    async def _validate_language_support(self, input_data: SentimentInput) -> List[str]:
        """Validate language support"""
        errors = []
        
        if input_data.language not in self.supported_languages:
            errors.append(
                f"Language '{input_data.language}' not supported. "
                f"Supported languages: {', '.join(self.supported_languages)}"
            )
        
        return errors
    
    async def _validate_analysis_config(self, input_data: SentimentInput) -> List[str]:
        """Validate analysis configuration"""
        errors = []
        
        # Check granularity support
        if input_data.granularity not in self.supported_granularities:
            granularity_names = [g.value for g in self.supported_granularities]
            errors.append(
                f"Granularity '{input_data.granularity.value}' not supported. "
                f"Supported: {', '.join(granularity_names)}"
            )
        
        # Validate granularity-specific requirements
        if input_data.granularity == AnalysisGranularity.ASPECT:
            if not input_data.aspects or len(input_data.aspects) == 0:
                errors.append("Aspects must be specified for aspect-based analysis")
        
        elif input_data.granularity == AnalysisGranularity.SENTENCE:
            # Check if text has enough sentences
            sentences = self._split_into_sentences(input_data.text)
            if len(sentences) < 2:
                errors.append("Text must contain at least 2 sentences for sentence-level analysis")
        
        return errors
    
    async def _validate_aspects(self, input_data: SentimentInput) -> List[str]:
        """Validate aspect-based analysis configuration"""
        errors = []
        
        if not input_data.aspects:
            return errors
        
        # Check number of aspects
        if len(input_data.aspects) > self.text_limits["max_aspects"]:
            errors.append(
                f"Too many aspects: {len(input_data.aspects)} "
                f"(maximum: {self.text_limits['max_aspects']})"
            )
        
        # Validate individual aspects
        for i, aspect in enumerate(input_data.aspects):
            if not aspect or len(aspect.strip()) < self.text_limits["min_aspect_length"]:
                errors.append(
                    f"Aspect {i+1} too short (minimum {self.text_limits['min_aspect_length']} characters)"
                )
            
            # Check if aspect contains only special characters
            if self._contains_only_special_chars(aspect):
                errors.append(f"Aspect {i+1} contains only special characters")
        
        # Check for duplicate aspects
        aspect_lower = [a.lower().strip() for a in input_data.aspects]
        if len(set(aspect_lower)) != len(aspect_lower):
            errors.append("Duplicate aspects found")
        
        return errors
    
    async def _validate_constraints(self, input_data: SentimentInput, options: Dict[str, Any]) -> List[str]:
        """Validate additional constraints"""
        errors = []
        
        # Check encoding issues
        try:
            input_data.text.encode('utf-8')
        except UnicodeEncodeError:
            errors.append("Text contains invalid characters")
        
        # Check for extremely repetitive content
        if self._is_extremely_repetitive(input_data.text):
            errors.append("Text appears to be extremely repetitive")
        
        # Validate context if provided
        if input_data.context:
            if len(input_data.context) > 10000:  # 10K character limit for context
                errors.append("Context text too long (maximum 10,000 characters)")
        
        # Check metadata constraints
        if input_data.metadata:
            if len(input_data.metadata) > 50:  # Limit metadata entries
                errors.append("Too many metadata entries (maximum 50)")
        
        return errors
    
    def _contains_only_special_chars(self, text: str) -> bool:
        """Check if text contains only special characters and whitespace"""
        # Remove alphanumeric characters and check if anything remains
        cleaned = re.sub(r'[a-zA-Z0-9\u00C0-\u017F\u4e00-\u9fff]', '', text)
        return len(cleaned.strip()) == len(text.strip()) and len(text.strip()) > 0
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences for validation"""
        # Simple sentence splitting (can be improved with NLP tools)
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _is_extremely_repetitive(self, text: str) -> bool:
        """Check if text is extremely repetitive"""
        words = text.lower().split()
        if len(words) < 10:
            return False
        
        # Check if more than 70% of words are the same
        word_counts = {}
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        most_common_count = max(word_counts.values())
        repetition_ratio = most_common_count / len(words)
        
        return repetition_ratio > 0.7
    
    async def validate_text_quality(self, text: str) -> tuple[bool, List[str], Dict[str, Any]]:
        """
        Validate text quality and provide quality metrics
        Returns: (is_good_quality, warnings, quality_metrics)
        """
        warnings = []
        metrics = {}
        
        # Calculate quality metrics
        word_count = len(text.split())
        char_count = len(text)
        sentence_count = len(self._split_into_sentences(text))
        
        metrics.update({
            "word_count": word_count,
            "character_count": char_count,
            "sentence_count": sentence_count,
            "avg_words_per_sentence": word_count / max(sentence_count, 1)
        })
        
        # Quality checks
        if word_count < 5:
            warnings.append("Very short text may produce unreliable results")
        
        if sentence_count == 1 and word_count > 50:
            warnings.append("Long single sentence may benefit from punctuation")
        
        if self._is_extremely_repetitive(text):
            warnings.append("Highly repetitive text may affect analysis accuracy")
        
        # Determine overall quality
        is_good_quality = len(warnings) == 0 and word_count >= 5
        
        return is_good_quality, warnings, metrics
    
    def get_validation_config(self) -> Dict[str, Any]:
        """Get current validation configuration"""
        return {
            "supported_languages": self.supported_languages,
            "supported_granularities": [g.value for g in self.supported_granularities],
            "text_limits": self.text_limits.copy(),
            "total_supported_languages": len(self.supported_languages)
        }
    
    def update_language_support(self, languages: List[str]):
        """Update supported languages"""
        self.supported_languages = languages
        logger.info(f"Updated supported languages: {len(languages)} languages")
    
    def update_text_limits(self, **limits):
        """Update text validation limits"""
        self.text_limits.update(limits)
        logger.info(f"Updated text limits: {limits}")


# Default instance
sentiment_validator = SentimentValidator()