# src/topic_modeling/application/services/text_preprocessor.py
"""
Text preprocessing service implementation - SRP compliance.
"""
import re
from typing import Dict, Any

from src.topic_modeling.domain.interfaces import TextPreprocessor


class DefaultTextPreprocessor(TextPreprocessor):
    """
    Default implementation of text preprocessing for topic modeling.
    Follows SRP - only responsible for text preprocessing operations.
    """
    
    def __init__(
        self,
        min_text_length: int = 100,
        max_text_length: int = 100000,
        min_word_count: int = 50,
        remove_urls: bool = True,
        remove_emails: bool = True,
        normalize_whitespace: bool = True,
        remove_special_chars: bool = True
    ):
        self.min_text_length = min_text_length
        self.max_text_length = max_text_length
        self.min_word_count = min_word_count
        self.remove_urls = remove_urls
        self.remove_emails = remove_emails
        self.normalize_whitespace = normalize_whitespace
        self.remove_special_chars = remove_special_chars
    
    async def preprocess_text(self, text: str, language: str) -> str:
        """Preprocess text for topic modeling."""
        if not text or not text.strip():
            return ""
        
        processed_text = text
        
        # Remove URLs if configured
        if self.remove_urls:
            processed_text = self._remove_urls(processed_text)
        
        # Remove email addresses if configured
        if self.remove_emails:
            processed_text = self._remove_emails(processed_text)
        
        # Normalize whitespace if configured
        if self.normalize_whitespace:
            processed_text = self._normalize_whitespace(processed_text)
        
        # Remove special characters if configured
        if self.remove_special_chars:
            processed_text = self._remove_special_characters(processed_text)
        
        # Language-specific preprocessing
        processed_text = await self._language_specific_preprocessing(processed_text, language)
        
        # Final cleanup
        processed_text = self._final_cleanup(processed_text)
        
        return processed_text.strip()
    
    async def validate_text(self, text: str) -> bool:
        """Validate text for topic modeling."""
        if not text or not isinstance(text, str):
            return False
        
        # Check text length
        if len(text) < self.min_text_length or len(text) > self.max_text_length:
            return False
        
        # Check word count
        word_count = len(text.split())
        if word_count < self.min_word_count:
            return False
        
        # Check for meaningful content
        if not self._has_meaningful_content(text):
            return False
        
        return True
    
    async def get_text_stats(self, text: str) -> Dict[str, Any]:
        """Get text statistics."""
        if not text:
            return {
                "character_count": 0,
                "word_count": 0,
                "sentence_count": 0,
                "paragraph_count": 0,
                "average_word_length": 0.0,
                "lexical_diversity": 0.0,
                "readability_score": 0.0
            }
        
        words = text.split()
        sentences = self._split_into_sentences(text)
        paragraphs = self._split_into_paragraphs(text)
        
        # Calculate lexical diversity (unique words / total words)
        unique_words = len(set(word.lower() for word in words))
        lexical_diversity = unique_words / len(words) if words else 0.0
        
        # Calculate average word length
        avg_word_length = sum(len(word) for word in words) / len(words) if words else 0.0
        
        # Calculate simple readability score
        readability_score = self._calculate_readability_score(text, words, sentences)
        
        return {
            "character_count": len(text),
            "word_count": len(words),
            "sentence_count": len(sentences),
            "paragraph_count": len(paragraphs),
            "average_word_length": avg_word_length,
            "lexical_diversity": lexical_diversity,
            "readability_score": readability_score,
            "unique_word_count": unique_words,
            "avg_sentence_length": len(words) / len(sentences) if sentences else 0.0
        }
    
    def _remove_urls(self, text: str) -> str:
        """Remove URLs from text."""
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        return re.sub(url_pattern, '', text)
    
    def _remove_emails(self, text: str) -> str:
        """Remove email addresses from text."""
        email_pattern = r'\S+@\S+'
        return re.sub(email_pattern, '', text)
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text."""
        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)
        
        # Replace multiple newlines with double newline
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove trailing spaces from lines
        text = re.sub(r' +\n', '\n', text)
        
        return text
    
    def _remove_special_characters(self, text: str) -> str:
        """Remove special characters while preserving basic punctuation."""
        # Keep letters, numbers, basic punctuation, and whitespace
        pattern = r'[^a-zA-Z0-9\s\.,!?;:\-\'"()\[\]]'
        return re.sub(pattern, ' ', text)
    
    async def _language_specific_preprocessing(self, text: str, language: str) -> str:
        """Apply language-specific preprocessing."""
        # This can be extended for different languages
        if language in ["en", "english"]:
            # English-specific preprocessing
            text = self._preprocess_english(text)
        elif language in ["es", "spanish"]:
            # Spanish-specific preprocessing
            text = self._preprocess_spanish(text)
        # Add more languages as needed
        
        return text
    
    def _preprocess_english(self, text: str) -> str:
        """English-specific preprocessing."""
        # Remove common contractions artifacts
        contractions = {
            "n't": " not",
            "'re": " are",
            "'ve": " have",
            "'ll": " will",
            "'d": " would",
            "'m": " am"
        }
        
        for contraction, expansion in contractions.items():
            text = text.replace(contraction, expansion)
        
        return text
    
    def _preprocess_spanish(self, text: str) -> str:
        """Spanish-specific preprocessing."""
        # Spanish-specific character normalization
        text = text.replace("ñ", "n")  # Optional: normalize ñ
        return text
    
    def _final_cleanup(self, text: str) -> str:
        """Final cleanup of processed text."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def _has_meaningful_content(self, text: str) -> bool:
        """Check if text has meaningful content for topic modeling."""
        # Remove whitespace and check remaining content
        cleaned = re.sub(r'\s+', '', text)
        
        # Must have at least some alphabetic characters
        alpha_count = sum(1 for char in cleaned if char.isalpha())
        
        # At least 50% of non-whitespace characters should be alphabetic
        if len(cleaned) == 0:
            return False
        
        alpha_ratio = alpha_count / len(cleaned)
        return alpha_ratio >= 0.5
    
    def _split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        sentence_endings = r'[.!?]+(?:\s|$)'
        sentences = re.split(sentence_endings, text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _split_into_paragraphs(self, text: str) -> list[str]:
        """Split text into paragraphs."""
        paragraphs = re.split(r'\n\s*\n', text.strip())
        return [p.strip() for p in paragraphs if p.strip()]
    
    def _calculate_readability_score(self, text: str, words: list, sentences: list) -> float:
        """Calculate a simple readability score."""
        if not words or not sentences:
            return 0.0
        
        # Simple readability based on average sentence length
        avg_sentence_length = len(words) / len(sentences)
        
        # Score based on sentence length (shorter = more readable)
        if avg_sentence_length <= 15:
            score = 1.0
        elif avg_sentence_length <= 20:
            score = 0.8
        elif avg_sentence_length <= 25:
            score = 0.6
        elif avg_sentence_length <= 30:
            score = 0.4
        else:
            score = 0.2
        
        return score