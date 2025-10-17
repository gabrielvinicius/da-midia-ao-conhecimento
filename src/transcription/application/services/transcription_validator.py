"""
Transcription Validator Service - Single Responsibility: Validation operations.
Follows SRP by handling only validation concerns.
"""
import re
from typing import Set
import structlog

from src.transcription.domain.interfaces import ITranscriptionValidator
from src.shared.exceptions.domain_exceptions import ValidationError

logger = structlog.get_logger(__name__)


class TranscriptionValidator(ITranscriptionValidator):
    """
    Validates transcription input and output following SRP.
    Single responsibility: All validation logic for transcriptions.
    """
    
    def __init__(
        self, 
        min_audio_size: int = 1024,  # 1KB minimum
        max_audio_size: int = 100 * 1024 * 1024,  # 100MB maximum
        supported_languages: Set[str] = None
    ):
        self.min_audio_size = min_audio_size
        self.max_audio_size = max_audio_size
        self.supported_languages = supported_languages or {
            "en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja", "ko"
        }
    
    def validate_audio_data(self, audio_data: bytes) -> None:
        """Validate audio data for transcription."""
        if not audio_data:
            raise ValidationError("Audio data cannot be empty")
        
        if len(audio_data) < self.min_audio_size:
            raise ValidationError(
                f"Audio file is too small for transcription. "
                f"Minimum size: {self.min_audio_size} bytes"
            )
        
        if len(audio_data) > self.max_audio_size:
            raise ValidationError(
                f"Audio file is too large for transcription. "
                f"Maximum size: {self.max_audio_size} bytes"
            )
        
        if not self._is_valid_audio_format(audio_data):
            raise ValidationError(
                "Invalid audio format. Supported formats: WAV, MP3, M4A, FLAC"
            )
        
        logger.debug("transcription.audio_validated", audio_size=len(audio_data))
    
    def validate_language_code(self, language: str) -> None:
        """Validate language code is supported."""
        if not language:
            raise ValidationError("Language code cannot be empty")
        
        normalized_language = language.lower().strip()
        if normalized_language not in self.supported_languages:
            raise ValidationError(
                f"Unsupported language: {language}. "
                f"Supported languages: {', '.join(sorted(self.supported_languages))}"
            )
        
        logger.debug("transcription.language_validated", language=normalized_language)
    
    def validate_transcription_quality(self, transcription: str, audio_data: bytes) -> None:
        """Validate transcription quality."""
        if not transcription or not transcription.strip():
            raise ValidationError("Generated transcription is empty")
        
        words = re.findall(r'\b\w+\b', transcription)
        if len(words) < 2:
            raise ValidationError(
                "Transcription does not contain enough meaningful words"
            )
        
        if self._is_repetitive(transcription):
            raise ValidationError(
                "Transcription contains repetitive patterns indicating poor quality"
            )
        
        logger.debug(
            "transcription.quality_validated",
            transcription_length=len(transcription),
            word_count=len(words)
        )
    
    def _is_valid_audio_format(self, audio_data: bytes) -> bool:
        """Check if audio data has valid format headers."""
        if len(audio_data) < 12:
            return False
        
        header = audio_data[:12]
        
        # Check for common audio format signatures
        return (
            header[:4] == b'RIFF' and header[8:12] == b'WAVE' or  # WAV
            header[:3] == b'ID3' or header[:2] == b'\xff\xfb' or  # MP3
            header[:4] == b'fLaC' or  # FLAC
            b'ftyp' in header[:12] or  # M4A/MP4
            header[:4] == b'OggS'  # OGG
        )
    
    def _is_repetitive(self, text: str) -> bool:
        """Check if text contains repetitive patterns."""
        words = text.lower().split()
        if len(words) < 10:
            return False
        
        # Check for repeated sequences
        for i in range(len(words) - 5):
            sequence = ' '.join(words[i:i+3])
            remaining_text = ' '.join(words[i+3:])
            if sequence in remaining_text:
                return True
        
        return False