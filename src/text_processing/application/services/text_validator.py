# src/text_processing/application/services/text_validator.py
"""
Text validation service implementation - SRP compliance.
"""
import re
from typing import Optional, Dict, Any
import langdetect

from src.text_processing.domain.interfaces import TextValidator


class TextValidationError(Exception):
    """Exception for text validation errors."""
    pass


class DefaultTextValidator(TextValidator):
    """
    Default implementation of text validation.
    Follows SRP - only responsible for text validation.
    """
    
    def __init__(
        self,
        min_length: int = 10,
        max_length: int = 1_000_000,  # 1M characters
        min_word_count: int = 5,
        allowed_languages: Optional[list] = None
    ):
        self.min_length = min_length
        self.max_length = max_length
        self.min_word_count = min_word_count
        self.allowed_languages = allowed_languages or []
    
    async def validate_content(self, text: str) -> bool:
        """Validate extracted text content."""
        try:
            # Basic length validation
            if len(text) < self.min_length:
                return False
            
            if len(text) > self.max_length:
                return False
            
            # Word count validation
            word_count = len(text.split())
            if word_count < self.min_word_count:
                return False
            
            # Check for meaningful content (not just whitespace/special chars)
            if not self._has_meaningful_content(text):
                return False
            
            # Language validation if specified
            if self.allowed_languages:
                language = await self.detect_language(text)
                if language and language not in self.allowed_languages:
                    return False
            
            return True
            
        except Exception:
            return False
    
    async def get_content_stats(self, text: str) -> Dict[str, Any]:
        """Get text content statistics."""
        words = text.split()
        sentences = self._count_sentences(text)
        paragraphs = self._count_paragraphs(text)
        
        return {
            "character_count": len(text),
            "character_count_no_spaces": len(text.replace(" ", "")),
            "word_count": len(words),
            "sentence_count": sentences,
            "paragraph_count": paragraphs,
            "average_word_length": sum(len(word) for word in words) / len(words) if words else 0,
            "average_sentence_length": len(words) / sentences if sentences > 0 else 0,
            "readability_score": self._calculate_readability_score(text, words, sentences)
        }
    
    async def detect_language(self, text: str) -> Optional[str]:
        """Detect text language."""
        try:
            # Use a sample for language detection (first 1000 chars)
            sample = text[:1000] if len(text) > 1000 else text
            
            # Clean sample for better detection
            cleaned_sample = self._clean_for_language_detection(sample)
            
            if len(cleaned_sample) < 50:  # Too short for reliable detection
                return None
            
            detected = langdetect.detect(cleaned_sample)
            return detected
            
        except Exception:
            return None
    
    def _has_meaningful_content(self, text: str) -> bool:
        """Check if text has meaningful content."""
        # Remove whitespace and check remaining content
        cleaned = re.sub(r'\s+', '', text)
        
        # Must have at least some alphabetic characters
        alpha_count = sum(1 for char in cleaned if char.isalpha())
        
        # At least 50% of non-whitespace characters should be alphabetic
        if len(cleaned) == 0:
            return False
        
        alpha_ratio = alpha_count / len(cleaned)
        return alpha_ratio >= 0.3  # At least 30% alphabetic content
    
    def _count_sentences(self, text: str) -> int:
        """Count sentences in text."""
        # Simple sentence counting using punctuation
        sentence_endings = re.findall(r'[.!?]+', text)
        return max(1, len(sentence_endings))  # At least 1 sentence
    
    def _count_paragraphs(self, text: str) -> int:
        """Count paragraphs in text."""
        # Split by double newlines or more
        paragraphs = re.split(r'\n\s*\n', text.strip())
        # Filter out empty paragraphs
        non_empty_paragraphs = [p for p in paragraphs if p.strip()]
        return max(1, len(non_empty_paragraphs))  # At least 1 paragraph
    
    def _calculate_readability_score(self, text: str, words: list, sentences: int) -> float:
        """Calculate a simple readability score (Flesch-like)."""
        if not words or sentences == 0:
            return 0.0
        
        # Count syllables (approximation)
        total_syllables = sum(self._count_syllables(word) for word in words)
        
        # Flesch Reading Ease formula (simplified)
        # Score = 206.835 - (1.015 × ASL) - (84.6 × ASW)
        # ASL = Average Sentence Length (words per sentence)
        # ASW = Average Syllables per Word
        
        asl = len(words) / sentences
        asw = total_syllables / len(words)
        
        score = 206.835 - (1.015 * asl) - (84.6 * asw)
        
        # Normalize to 0-100 range
        return max(0, min(100, score))
    
    def _count_syllables(self, word: str) -> int:
        """Count syllables in a word (approximation)."""
        word = word.lower().strip()
        if not word:
            return 0
        
        # Remove non-alphabetic characters
        word = re.sub(r'[^a-z]', '', word)
        
        if not word:
            return 0
        
        # Count vowel groups
        vowels = 'aeiouy'
        syllable_count = 0
        prev_was_vowel = False
        
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_was_vowel:
                syllable_count += 1
            prev_was_vowel = is_vowel
        
        # Handle silent 'e'
        if word.endswith('e'):
            syllable_count -= 1
        
        # Every word has at least one syllable
        return max(1, syllable_count)
    
    def _clean_for_language_detection(self, text: str) -> str:
        """Clean text for better language detection."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)
        
        # Remove numbers and special characters (keep basic punctuation)
        text = re.sub(r'[^a-zA-Z\s.!?]', ' ', text)
        
        # Clean up whitespace again
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text