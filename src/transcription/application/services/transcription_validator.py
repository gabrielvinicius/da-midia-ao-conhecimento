# src/transcription/application/services/transcription_validator.py
"""
Transcription validation service implementation - SRP compliance.
"""
from typing import Dict, Any
import re

from src.transcription.domain.interfaces import TranscriptionValidator


class DefaultTranscriptionValidator(TranscriptionValidator):
    """
    Default implementation of transcription validation.
    Follows SRP - only responsible for validation operations.
    """
    
    def __init__(
        self,
        min_text_length: int = 1,
        max_text_length: int = 1_000_000,
        min_confidence: float = 0.0,
        valid_languages: list = None
    ):
        self.min_text_length = min_text_length
        self.max_text_length = max_text_length
        self.min_confidence = min_confidence
        self.valid_languages = valid_languages or []
    
    async def validate_result(self, result: Dict[str, Any]) -> bool:
        """Validate transcription result."""
        try:
            # Check required fields
            if not isinstance(result, dict):
                return False
            
            # Check text field
            text = result.get("text", "")
            if not isinstance(text, str):
                return False
            
            # Check text length
            if len(text) < self.min_text_length or len(text) > self.max_text_length:
                return False
            
            # Check confidence if provided
            confidence = result.get("confidence", 1.0)
            if not isinstance(confidence, (int, float)) or confidence < self.min_confidence:
                return False
            
            # Check language if provided and we have restrictions
            language = result.get("language", "")
            if self.valid_languages and language not in self.valid_languages:
                return False
            
            # Validate segments if present
            segments = result.get("segments", [])
            if segments and not await self._validate_segments(segments):
                return False
            
            # Check for meaningful content
            if not await self._has_meaningful_content(text):
                return False
            
            return True
            
        except Exception:
            return False
    
    async def validate_language(self, language: str) -> bool:
        """Validate language code."""
        if not language or not isinstance(language, str):
            return False
        
        # Allow 'auto' for automatic detection
        if language == "auto":
            return True
        
        # Check if it's a valid ISO 639-1 language code (2 characters)
        if len(language) == 2 and language.isalpha():
            return True
        
        # Check if it's in our valid languages list
        if self.valid_languages and language in self.valid_languages:
            return True
        
        # Check common language codes
        common_languages = {
            "en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh",
            "ar", "hi", "tr", "pl", "nl", "sv", "da", "no", "fi", "hu"
        }
        
        return language in common_languages
    
    async def get_result_quality_score(self, result: Dict[str, Any]) -> float:
        """Get quality score for transcription result."""
        try:
            score = 0.0
            max_score = 100.0
            
            # Text content quality (40 points)
            text = result.get("text", "")
            if text:
                score += 20.0  # Has text
                
                # Check text quality
                if await self._has_meaningful_content(text):
                    score += 10.0
                
                # Check text length (reasonable length gets points)
                if 10 <= len(text) <= 10000:
                    score += 10.0
            
            # Confidence score (30 points)
            confidence = result.get("confidence", 0.0)
            if isinstance(confidence, (int, float)):
                score += confidence * 30.0
            
            # Segments quality (20 points)
            segments = result.get("segments", [])
            if segments:
                score += 10.0  # Has segments
                
                # Check segments quality
                if await self._validate_segments(segments):
                    score += 10.0
            
            # Language detection (10 points)
            language = result.get("language", "")
            if language and language != "unknown":
                score += 10.0
            
            return min(score, max_score) / max_score
            
        except Exception:
            return 0.0
    
    async def _validate_segments(self, segments: list) -> bool:
        """Validate transcription segments."""
        try:
            if not isinstance(segments, list):
                return False
            
            for segment in segments:
                if not isinstance(segment, dict):
                    return False
                
                # Check required fields
                if "text" not in segment:
                    return False
                
                # Check timestamps if present
                start = segment.get("start")
                end = segment.get("end")
                
                if start is not None and end is not None:
                    if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
                        return False
                    
                    if start < 0 or end < 0 or start > end:
                        return False
                
                # Check text content
                text = segment.get("text", "")
                if not isinstance(text, str):
                    return False
            
            return True
            
        except Exception:
            return False
    
    async def _has_meaningful_content(self, text: str) -> bool:
        """Check if text has meaningful content."""
        if not text or not text.strip():
            return False
        
        # Remove whitespace and check remaining content
        cleaned = re.sub(r'\s+', '', text)
        
        # Must have at least some alphabetic characters
        alpha_count = sum(1 for char in cleaned if char.isalpha())
        
        # At least 30% of characters should be alphabetic
        if len(cleaned) == 0:
            return False
        
        alpha_ratio = alpha_count / len(cleaned)
        if alpha_ratio < 0.3:
            return False
        
        # Check for common non-content patterns
        non_content_patterns = [
            r'^[\s\.\-_\(\)\[\]]*$',  # Only punctuation and whitespace
            r'^[0-9\s\.\-_\(\)\[\]]*$',  # Only numbers and punctuation
            r'^[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]*$'  # Only special characters
        ]
        
        for pattern in non_content_patterns:
            if re.match(pattern, text):
                return False
        
        return True
    
    def _calculate_text_complexity(self, text: str) -> float:
        """Calculate text complexity score."""
        if not text:
            return 0.0
        
        words = text.split()
        sentences = re.split(r'[.!?]+', text)
        
        # Basic complexity metrics
        avg_word_length = sum(len(word) for word in words) / len(words) if words else 0
        avg_sentence_length = len(words) / len(sentences) if sentences else 0
        
        # Vocabulary diversity (unique words / total words)
        unique_words = len(set(word.lower() for word in words))
        vocabulary_diversity = unique_words / len(words) if words else 0
        
        # Combine metrics (normalized to 0-1)
        complexity = (
            min(avg_word_length / 10, 1.0) * 0.3 +
            min(avg_sentence_length / 20, 1.0) * 0.3 +
            vocabulary_diversity * 0.4
        )
        
        return complexity