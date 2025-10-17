# src/summarization/application/services/summarization_validator.py
"""
Summarization Validation Service - Single Responsibility Principle
Extracted from BaseSummarizationTemplate God Class (514 lines)
Handles all summarization input validation and constraint checking
"""

import re
from typing import Dict, Any, List, Optional
from enum import Enum

from src.summarization.infrastructure.templates.summarization_templates import (
    SummarizationInput, SummaryType, SummaryLength
)
from src.shared.infrastructure.logging_config import get_logger

logger = get_logger("summarization_validator")


class SummarizationValidator:
    """
    Summarization validation with Single Responsibility:
    Validate text inputs, language support, and summarization constraints
    """
    
    def __init__(self):
        self.supported_languages = [
            "en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh"
        ]
        self.supported_types = list(SummaryType)
        self.supported_lengths = list(SummaryLength)
        self.text_limits = {
            "min_length": 100,
            "max_length": 1000000,
            "min_words": 20,
            "max_words": 200000
        }
        self.length_constraints = {
            SummaryLength.SHORT: {"min_ratio": 0.05, "max_ratio": 0.15},
            SummaryLength.MEDIUM: {"min_ratio": 0.10, "max_ratio": 0.25},
            SummaryLength.LONG: {"min_ratio": 0.20, "max_ratio": 0.40},
            SummaryLength.CUSTOM: {"min_ratio": 0.01, "max_ratio": 0.80}
        }
    
    async def validate_input(
        self, 
        input_data: SummarizationInput, 
        options: Dict[str, Any] = None
    ) -> tuple[bool, List[str]]:
        """
        Validate summarization input
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
        
        # Validate summarization configuration
        config_errors = await self._validate_summarization_config(input_data)
        errors.extend(config_errors)
        
        # Validate length constraints
        length_errors = await self._validate_length_constraints(input_data)
        errors.extend(length_errors)
        
        # Validate additional constraints
        constraint_errors = await self._validate_constraints(input_data, options)
        errors.extend(constraint_errors)
        
        is_valid = len(errors) == 0
        
        if is_valid:
            logger.info(f"Summarization input validation passed: {input_data.summary_type.value}/{input_data.summary_length.value}")
        else:
            logger.warning(f"Summarization input validation failed: {len(errors)} errors")
            for error in errors:
                logger.warning(f"  - {error}")
        
        return is_valid, errors
    
    async def _validate_text_content(self, input_data: SummarizationInput, options: Dict[str, Any]) -> List[str]:
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
        
        # Check word count limits
        words = input_data.text.split()
        word_count = len(words)
        
        if word_count < self.text_limits["min_words"]:
            errors.append(
                f"Text too short: {word_count} words (minimum: {self.text_limits['min_words']})"
            )
        
        if word_count > self.text_limits["max_words"]:
            errors.append(
                f"Text too long: {word_count} words (maximum: {self.text_limits['max_words']})"
            )
        
        # Check for potentially problematic content
        if self._contains_only_special_chars(input_data.text):
            errors.append("Text contains only special characters or whitespace")
        
        return errors
    
    async def _validate_language_support(self, input_data: SummarizationInput) -> List[str]:
        """Validate language support"""
        errors = []
        
        if input_data.language not in self.supported_languages:
            errors.append(
                f"Language '{input_data.language}' not supported. "
                f"Supported languages: {', '.join(self.supported_languages)}"
            )
        
        return errors
    
    async def _validate_summarization_config(self, input_data: SummarizationInput) -> List[str]:
        """Validate summarization configuration"""
        errors = []
        
        # Check summary type support
        if input_data.summary_type not in self.supported_types:
            type_names = [t.value for t in self.supported_types]
            errors.append(
                f"Summary type '{input_data.summary_type.value}' not supported. "
                f"Supported types: {', '.join(type_names)}"
            )
        
        # Check summary length support
        if input_data.summary_length not in self.supported_lengths:
            length_names = [l.value for l in self.supported_lengths]
            errors.append(
                f"Summary length '{input_data.summary_length.value}' not supported. "
                f"Supported lengths: {', '.join(length_names)}"
            )
        
        # Validate type-specific requirements
        if input_data.summary_type == SummaryType.HEADLINE:
            # Headlines should be short
            if input_data.summary_length not in [SummaryLength.SHORT, SummaryLength.CUSTOM]:
                errors.append("Headlines should use SHORT or CUSTOM length")
        
        elif input_data.summary_type == SummaryType.BULLET_POINTS:
            # Bullet points work better with medium to long text
            word_count = len(input_data.text.split())
            if word_count < 100:
                errors.append("Bullet points require at least 100 words of text")
        
        return errors
    
    async def _validate_length_constraints(self, input_data: SummarizationInput) -> List[str]:
        """Validate summary length constraints"""
        errors = []
        
        if input_data.summary_length == SummaryLength.CUSTOM:
            # Validate custom length parameters
            if not input_data.max_length:
                errors.append("max_length required for custom summary length")
                return errors
            
            if input_data.min_length and input_data.min_length > input_data.max_length:
                errors.append("min_length cannot be greater than max_length")
            
            if input_data.max_length <= 0:
                errors.append("max_length must be positive")
            
            if input_data.min_length and input_data.min_length < 0:
                errors.append("min_length cannot be negative")
            
            # Check if custom length is reasonable relative to input
            input_words = len(input_data.text.split())
            if input_data.max_length > input_words:
                errors.append(
                    f"max_length ({input_data.max_length}) cannot exceed input length ({input_words} words)"
                )
        
        else:
            # Validate predefined length constraints
            constraints = self.length_constraints.get(input_data.summary_length)
            if constraints:
                input_words = len(input_data.text.split())
                min_expected = int(input_words * constraints["min_ratio"])
                max_expected = int(input_words * constraints["max_ratio"])
                
                # These are warnings, not errors, for predefined lengths
                if input_words < 50:  # Very short input
                    errors.append(f"Text may be too short for {input_data.summary_length.value} summary")
        
        return errors
    
    async def _validate_constraints(self, input_data: SummarizationInput, options: Dict[str, Any]) -> List[str]:
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
        
        # Validate custom instructions if provided
        if input_data.custom_instructions:
            if len(input_data.custom_instructions) > 1000:
                errors.append("Custom instructions too long (maximum 1000 characters)")
            
            # Check for potentially problematic instructions
            if self._contains_problematic_instructions(input_data.custom_instructions):
                errors.append("Custom instructions contain potentially problematic content")
        
        # Check metadata constraints
        if input_data.metadata:
            if len(input_data.metadata) > 20:
                errors.append("Too many metadata entries (maximum 20)")
        
        return errors
    
    def _contains_only_special_chars(self, text: str) -> bool:
        """Check if text contains only special characters and whitespace"""
        # Remove alphanumeric characters and check if anything meaningful remains
        cleaned = re.sub(r'[a-zA-Z0-9\u00C0-\u017F\u4e00-\u9fff]', '', text)
        return len(cleaned.strip()) == len(text.strip()) and len(text.strip()) > 0
    
    def _is_extremely_repetitive(self, text: str) -> bool:
        """Check if text is extremely repetitive"""
        words = text.lower().split()
        if len(words) < 20:
            return False
        
        # Check if more than 60% of words are the same
        word_counts = {}
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        most_common_count = max(word_counts.values())
        repetition_ratio = most_common_count / len(words)
        
        return repetition_ratio > 0.6
    
    def _contains_problematic_instructions(self, instructions: str) -> bool:
        """Check for potentially problematic custom instructions"""
        problematic_patterns = [
            r'ignore\s+previous',
            r'system\s+prompt',
            r'pretend\s+to\s+be',
            r'act\s+as\s+if',
        ]
        
        instructions_lower = instructions.lower()
        for pattern in problematic_patterns:
            if re.search(pattern, instructions_lower):
                return True
        
        return False
    
    async def validate_text_quality(self, text: str) -> tuple[bool, List[str], Dict[str, Any]]:
        """
        Validate text quality for summarization
        Returns: (is_good_quality, warnings, quality_metrics)
        """
        warnings = []
        metrics = {}
        
        # Calculate quality metrics
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        word_count = len(text.split())
        char_count = len(text)
        sentence_count = len(sentences)
        avg_sentence_length = word_count / max(sentence_count, 1)
        
        metrics.update({
            "word_count": word_count,
            "character_count": char_count,
            "sentence_count": sentence_count,
            "avg_sentence_length": avg_sentence_length,
            "text_density": word_count / max(char_count, 1)
        })
        
        # Quality checks
        if sentence_count < 3:
            warnings.append("Very few sentences may produce limited summary options")
        
        if avg_sentence_length > 50:
            warnings.append("Very long sentences may affect summary readability")
        
        if avg_sentence_length < 5:
            warnings.append("Very short sentences may indicate fragmented text")
        
        if self._is_extremely_repetitive(text):
            warnings.append("Highly repetitive text may result in redundant summaries")
        
        # Check for list-like content
        if self._appears_to_be_list(text):
            warnings.append("List-like content may work better with bullet point summaries")
        
        # Determine overall quality
        is_good_quality = (
            len(warnings) <= 1 and 
            sentence_count >= 3 and 
            5 <= avg_sentence_length <= 30
        )
        
        return is_good_quality, warnings, metrics
    
    def _appears_to_be_list(self, text: str) -> bool:
        """Check if text appears to be a list"""
        lines = text.split('\n')
        list_indicators = 0
        
        for line in lines:
            line = line.strip()
            if re.match(r'^[\d\-\*\•]', line) or line.startswith('- '):
                list_indicators += 1
        
        return list_indicators > len(lines) * 0.3  # >30% of lines look like list items
    
    def get_validation_config(self) -> Dict[str, Any]:
        """Get current validation configuration"""
        return {
            "supported_languages": self.supported_languages,
            "supported_types": [t.value for t in self.supported_types],
            "supported_lengths": [l.value for l in self.supported_lengths],
            "text_limits": self.text_limits.copy(),
            "length_constraints": {
                k.value: v for k, v in self.length_constraints.items()
            }
        }
    
    def update_text_limits(self, **limits):
        """Update text validation limits"""
        self.text_limits.update(limits)
        logger.info(f"Updated text limits: {limits}")
    
    def add_supported_language(self, language: str):
        """Add supported language"""
        if language not in self.supported_languages:
            self.supported_languages.append(language)
            logger.info(f"Added supported language: {language}")


# Default instance
summarization_validator = SummarizationValidator()