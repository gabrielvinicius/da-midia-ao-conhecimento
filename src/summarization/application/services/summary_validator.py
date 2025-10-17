"""
Summary Validator Service - Single Responsibility: Validation operations.
Follows SRP by handling only validation concerns.
"""
import re
from typing import Dict, Any
import structlog

from src.summarization.domain.interfaces import ISummaryValidator
from src.shared.exceptions.domain_exceptions import ValidationError

logger = structlog.get_logger(__name__)


class SummaryValidator(ISummaryValidator):
    """
    Validates summary input and output following SRP.
    Single responsibility: All validation logic for summaries.
    """
    
    def __init__(self, min_text_length: int = 100, max_text_length: int = 50000):
        self.min_text_length = min_text_length
        self.max_text_length = max_text_length
    
    def validate_input_text(self, text: str) -> None:
        """
        Validate input text for summarization.
        
        Args:
            text: Text to validate
            
        Raises:
            ValidationError: If text is invalid
        """
        if not text or not text.strip():
            raise ValidationError("Text content cannot be empty")
        
        if len(text) < self.min_text_length:
            raise ValidationError(
                f"Text is too short for summarization. "
                f"Minimum length: {self.min_text_length} characters"
            )
        
        if len(text) > self.max_text_length:
            raise ValidationError(
                f"Text is too long for summarization. "
                f"Maximum length: {self.max_text_length} characters"
            )
        
        # Check for meaningful content (not just whitespace/special chars)
        word_count = len(re.findall(r'\b\w+\b', text))
        if word_count < 20:
            raise ValidationError(
                "Text does not contain enough meaningful words for summarization"
            )
        
        logger.debug(
            "summary.input_validated",
            text_length=len(text),
            word_count=word_count
        )
    
    def validate_summary_quality(self, summary: str, original_text: str) -> None:
        """
        Validate generated summary quality.
        
        Args:
            summary: Generated summary
            original_text: Original text
            
        Raises:
            ValidationError: If summary quality is poor
        """
        if not summary or not summary.strip():
            raise ValidationError("Generated summary is empty")
        
        # Check compression ratio
        compression_ratio = len(summary) / len(original_text)
        if compression_ratio > 0.8:
            raise ValidationError(
                f"Summary is too long compared to original text. "
                f"Compression ratio: {compression_ratio:.2f}"
            )
        
        if compression_ratio < 0.05:
            raise ValidationError(
                f"Summary is too short and may lose important information. "
                f"Compression ratio: {compression_ratio:.2f}"
            )
        
        # Check for meaningful content
        summary_words = len(re.findall(r'\b\w+\b', summary))
        if summary_words < 5:
            raise ValidationError("Summary does not contain enough meaningful words")
        
        # Check for repetitive content
        if self._is_repetitive(summary):
            raise ValidationError("Summary contains repetitive content")
        
        logger.debug(
            "summary.quality_validated",
            summary_length=len(summary),
            compression_ratio=compression_ratio,
            summary_words=summary_words
        )
    
    def validate_summary_length(self, summary: str, max_length: int) -> None:
        """
        Validate summary length constraints.
        
        Args:
            summary: Summary to validate
            max_length: Maximum allowed length
            
        Raises:
            ValidationError: If summary exceeds length limit
        """
        if len(summary) > max_length:
            raise ValidationError(
                f"Summary exceeds maximum length. "
                f"Length: {len(summary)}, Maximum: {max_length}"
            )
        
        logger.debug(
            "summary.length_validated",
            summary_length=len(summary),
            max_length=max_length
        )
    
    def _is_repetitive(self, text: str) -> bool:
        """
        Check if text contains repetitive patterns.
        
        Args:
            text: Text to check
            
        Returns:
            bool: True if text is repetitive
        """
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) < 2:
            return False
        
        # Check for identical or very similar sentences
        for i, sentence1 in enumerate(sentences):
            for sentence2 in sentences[i+1:]:
                # Simple similarity check based on common words
                words1 = set(sentence1.lower().split())
                words2 = set(sentence2.lower().split())
                
                if len(words1) > 0 and len(words2) > 0:
                    similarity = len(words1.intersection(words2)) / len(words1.union(words2))
                    if similarity > 0.8:  # 80% similarity threshold
                        return True
        
        return False