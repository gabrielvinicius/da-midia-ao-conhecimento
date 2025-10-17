# src/transcription/application/services/transcription_processor.py
"""
Transcription Processing Service - Single Responsibility Principle
Extracted from BaseTranscriptionTemplate God Class (421 lines)
Handles core audio transcription processing operations
"""

import tempfile
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.transcription.infrastructure.templates.transcription_templates import TranscriptionInput, AudioFormat
from src.transcription.domain.transcription import Transcription
from src.shared.infrastructure.logging_config import get_logger

logger = get_logger("transcription_processor")


class TranscriptionProcessor:
    """
    Transcription processing with Single Responsibility:
    Execute audio transcription operations and audio processing
    """
    
    def __init__(self, provider_name: str = "default", model_name: str = "default"):
        self.provider_name = provider_name
        self.model_name = model_name
        self.session_id: Optional[str] = None
        self.processed_audio: Optional[bytes] = None
        self.temp_files: List[str] = []
        
        # Processing cache for performance
        self.processing_cache = {}
        self.cache_enabled = True
        
    async def process_transcription(
        self, 
        input_data: TranscriptionInput, 
        options: Dict[str, Any] = None
    ) -> Transcription:
        """
        Main transcription processing entry point
        Returns complete transcription result
        """
        options = options or {}
        
        try:
            # Initialize processing session
            await self._initialize_processing(input_data, options)
            
            # Preprocess audio
            self.processed_audio = await self._preprocess_audio(input_data.audio_data, input_data, options)
            
            # Perform transcription
            transcription_text = await self._perform_transcription(self.processed_audio, input_data, options)
            
            # Post-process transcription text
            final_text = await self._post_process_text(transcription_text, options)
            
            # Extract additional information
            timestamps = await self._extract_timestamps(transcription_text, input_data, options)
            speaker_info = await self._extract_speaker_information(transcription_text, options)
            confidence = await self._calculate_confidence(transcription_text, input_data)
            
            # Create Transcription object
            transcription = Transcription(
                text=final_text,
                language=input_data.language,
                confidence=confidence
            )
            
            # Add optional information
            if timestamps:
                transcription.timestamps = timestamps
            if speaker_info:
                transcription.speakers = speaker_info
            
            logger.info(f"Transcription completed: {len(final_text)} characters")
            return transcription
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise
        finally:
            # Cleanup temporary files
            await self._cleanup_temp_files()
    
    async def _initialize_processing(self, input_data: TranscriptionInput, options: Dict[str, Any]):
        """Initialize processing session"""
        self.session_id = f"{self.provider_name}_{int(datetime.now().timestamp())}_{hash(input_data.audio_data) % 10000}"
        
        # Clear previous state
        self.processed_audio = None
        self.temp_files = []
        
        logger.debug(f"Initialized transcription processing session: {self.session_id}")
    
    async def _preprocess_audio(self, audio_data: bytes, input_data: TranscriptionInput, options: Dict[str, Any]) -> bytes:
        """Preprocess audio data for transcription"""
        
        if not options.get("enable_preprocessing", True):
            return audio_data
        
        processed = audio_data
        
        # Normalize audio format if needed
        if options.get("normalize_format", False):
            processed = await self._normalize_audio_format(processed, input_data)
        
        # Apply noise reduction if requested
        if options.get("noise_reduction", False):
            processed = await self._apply_noise_reduction(processed, input_data)
        
        # Normalize volume if requested
        if options.get("normalize_volume", False):
            processed = await self._normalize_volume(processed, input_data)
        
        # Convert to optimal format for transcription
        if options.get("optimize_for_transcription", True):
            processed = await self._optimize_for_transcription(processed, input_data)
        
        logger.debug(f"Audio preprocessing completed: {len(audio_data)} -> {len(processed)} bytes")
        return processed
    
    async def _normalize_audio_format(self, audio_data: bytes, input_data: TranscriptionInput) -> bytes:
        """Normalize audio format (mock implementation)"""
        
        # In production, would use ffmpeg or similar
        # Mock implementation: return as-is
        logger.debug(f"Normalized audio format: {input_data.audio_format.value}")
        return audio_data
    
    async def _apply_noise_reduction(self, audio_data: bytes, input_data: TranscriptionInput) -> bytes:
        """Apply noise reduction (mock implementation)"""
        
        # In production, would use audio processing libraries
        # Mock implementation: return as-is
        logger.debug("Applied noise reduction")
        return audio_data
    
    async def _normalize_volume(self, audio_data: bytes, input_data: TranscriptionInput) -> bytes:
        """Normalize audio volume (mock implementation)"""
        
        # In production, would normalize audio levels
        # Mock implementation: return as-is
        logger.debug("Normalized audio volume")
        return audio_data
    
    async def _optimize_for_transcription(self, audio_data: bytes, input_data: TranscriptionInput) -> bytes:
        """Optimize audio for transcription (mock implementation)"""
        
        # In production, would:
        # - Convert to mono if stereo
        # - Resample to optimal rate (16kHz for most models)
        # - Apply filters to enhance speech
        
        logger.debug("Optimized audio for transcription")
        return audio_data
    
    async def _perform_transcription(self, audio_data: bytes, input_data: TranscriptionInput, options: Dict[str, Any]) -> str:
        """Perform actual transcription (mock implementation)"""
        
        # Check cache
        cache_key = f"transcription_{hash(audio_data)}"
        if self.cache_enabled and cache_key in self.processing_cache:
            logger.debug("Using cached transcription result")
            return self.processing_cache[cache_key]
        
        # Mock transcription - in production would call actual ASR model
        if input_data.language == "en":
            transcription_text = "This is a mock transcription of the English audio content."
        elif input_data.language == "es":
            transcription_text = "Esta es una transcripción simulada del contenido de audio en español."
        elif input_data.language == "fr":
            transcription_text = "Ceci est une transcription simulée du contenu audio français."
        else:
            transcription_text = f"Mock transcription in {input_data.language} language."
        
        # Add provider-specific processing
        if self.provider_name == "whisper":
            transcription_text = f"[Whisper] {transcription_text}"
        elif self.provider_name == "fast_whisper":
            transcription_text = f"[FastWhisper] {transcription_text}"
        elif self.provider_name == "huggingface":
            transcription_text = f"[HuggingFace] {transcription_text}"
        
        # Cache result
        if self.cache_enabled:
            self.processing_cache[cache_key] = transcription_text
        
        return transcription_text
    
    async def _post_process_text(self, text: str, options: Dict[str, Any]) -> str:
        """Post-process transcription text"""
        
        if not options.get("enable_postprocessing", True):
            return text
        
        processed = text
        
        # Clean up common transcription artifacts
        if options.get("clean_artifacts", True):
            processed = self._clean_transcription_artifacts(processed)
        
        # Apply punctuation if requested
        if options.get("add_punctuation", False):
            processed = await self._add_punctuation(processed)
        
        # Capitalize sentences if requested
        if options.get("capitalize_sentences", True):
            processed = self._capitalize_sentences(processed)
        
        # Remove filler words if requested
        if options.get("remove_fillers", False):
            processed = self._remove_filler_words(processed)
        
        return processed.strip()
    
    def _clean_transcription_artifacts(self, text: str) -> str:
        """Clean common transcription artifacts"""
        
        # Remove repeated words
        words = text.split()
        cleaned_words = []
        prev_word = None
        
        for word in words:
            # Skip if same as previous word (simple deduplication)
            if word != prev_word or len(cleaned_words) == 0:
                cleaned_words.append(word)
            prev_word = word
        
        return ' '.join(cleaned_words)
    
    async def _add_punctuation(self, text: str) -> str:
        """Add punctuation to text (mock implementation)"""
        
        # In production, would use punctuation restoration model
        # Mock implementation: add periods at sentence boundaries
        
        sentences = text.split('. ')
        punctuated = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and not sentence.endswith(('.', '!', '?')):
                sentence += '.'
            punctuated.append(sentence)
        
        return ' '.join(punctuated)
    
    def _capitalize_sentences(self, text: str) -> str:
        """Capitalize first letter of sentences"""
        
        import re
        
        # Capitalize after sentence endings
        def capitalize_match(match):
            return match.group(0).upper()
        
        # Capitalize first letter
        if text:
            text = text[0].upper() + text[1:] if len(text) > 1 else text.upper()
        
        # Capitalize after sentence endings
        text = re.sub(r'([.!?]\s+)([a-z])', lambda m: m.group(1) + m.group(2).upper(), text)
        
        return text
    
    def _remove_filler_words(self, text: str) -> str:
        """Remove filler words from transcription"""
        
        filler_words = {
            "en": ["um", "uh", "ah", "er", "like", "you know"],
            "es": ["eh", "este", "pues"],
            "fr": ["euh", "alors", "donc"],
        }
        
        # Default to English fillers
        fillers = filler_words.get("en", [])
        
        words = text.split()
        filtered_words = [word for word in words if word.lower() not in fillers]
        
        return ' '.join(filtered_words)
    
    async def _extract_timestamps(self, text: str, input_data: TranscriptionInput, options: Dict[str, Any]) -> Optional[List[Dict]]:
        """Extract word-level timestamps (mock implementation)"""
        
        if not options.get("word_timestamps", False):
            return None
        
        words = text.split()
        timestamps = []
        current_time = 0.0
        
        for word in words:
            timestamps.append({
                "word": word,
                "start": round(current_time, 2),
                "end": round(current_time + 0.5, 2),
                "confidence": 0.95
            })
            current_time += 0.6  # Assume 0.6 seconds per word
        
        return timestamps
    
    async def _extract_speaker_information(self, text: str, options: Dict[str, Any]) -> Optional[List[Dict]]:
        """Extract speaker diarization information (mock implementation)"""
        
        if not options.get("speaker_diarization", False):
            return None
        
        # Mock speaker information
        speakers = [
            {
                "speaker_id": "SPEAKER_00",
                "start_time": 0.0,
                "end_time": len(text.split()) * 0.6,
                "text": text
            }
        ]
        
        return speakers
    
    async def _calculate_confidence(self, text: str, input_data: TranscriptionInput) -> float:
        """Calculate transcription confidence score (mock implementation)"""
        
        # Mock confidence calculation based on various factors
        base_confidence = 0.85
        
        # Adjust based on text length
        word_count = len(text.split())
        if word_count < 5:
            confidence_adjustment = -0.15
        elif word_count > 100:
            confidence_adjustment = 0.10
        else:
            confidence_adjustment = 0.0
        
        # Adjust based on language
        if input_data.language == "en":
            language_adjustment = 0.05
        else:
            language_adjustment = -0.05
        
        final_confidence = base_confidence + confidence_adjustment + language_adjustment
        return max(0.0, min(1.0, final_confidence))
    
    async def _cleanup_temp_files(self):
        """Clean up temporary files created during processing"""
        
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    logger.debug(f"Cleaned up temp file: {temp_file}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {temp_file}: {e}")
        
        self.temp_files.clear()
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            "provider": self.provider_name,
            "model": self.model_name,
            "current_session": self.session_id,
            "cache_enabled": self.cache_enabled,
            "cached_results": len(self.processing_cache),
            "temp_files_count": len(self.temp_files)
        }
    
    def clear_cache(self):
        """Clear processing cache"""
        self.processing_cache.clear()
        logger.info("Processing cache cleared")
    
    def enable_cache(self, enabled: bool = True):
        """Enable or disable result caching"""
        self.cache_enabled = enabled
        logger.info(f"Processing cache {'enabled' if enabled else 'disabled'}")


# Default instance
transcription_processor = TranscriptionProcessor()