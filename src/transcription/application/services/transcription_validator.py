# src/transcription/application/services/transcription_validator.py
"""
Transcription Validation Service - Single Responsibility Principle
Extracted from BaseTranscriptionTemplate God Class (421 lines)
Handles all transcription input validation and audio constraint checking
"""

import struct
from typing import Dict, Any, List, Optional
from enum import Enum

from src.transcription.infrastructure.templates.transcription_templates import TranscriptionInput, AudioFormat
from src.shared.infrastructure.logging_config import get_logger

logger = get_logger("transcription_validator")


class TranscriptionValidator:
    """
    Transcription validation with Single Responsibility:
    Validate audio inputs, format support, and transcription constraints
    """
    
    def __init__(self):
        self.supported_languages = [
            "en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja", "ko", "ar", "hi"
        ]
        self.supported_formats = list(AudioFormat)
        self.audio_limits = {
            "min_size_bytes": 1024,  # 1KB minimum
            "max_size_mb": 25,  # 25MB maximum
            "min_duration_seconds": 0.1,
            "max_duration_seconds": 3600,  # 1 hour
            "min_sample_rate": 8000,
            "max_sample_rate": 48000,
            "supported_channels": [1, 2]  # mono, stereo
        }
    
    async def validate_input(
        self, 
        input_data: TranscriptionInput, 
        options: Dict[str, Any] = None
    ) -> tuple[bool, List[str]]:
        """
        Validate transcription input
        Returns: (is_valid, error_messages)
        """
        errors = []
        options = options or {}
        
        # Validate audio data
        audio_errors = await self._validate_audio_data(input_data, options)
        errors.extend(audio_errors)
        
        # Validate audio format
        format_errors = await self._validate_audio_format(input_data)
        errors.extend(format_errors)
        
        # Validate language support
        language_errors = await self._validate_language_support(input_data)
        errors.extend(language_errors)
        
        # Validate audio properties
        properties_errors = await self._validate_audio_properties(input_data)
        errors.extend(properties_errors)
        
        # Validate additional constraints
        constraint_errors = await self._validate_constraints(input_data, options)
        errors.extend(constraint_errors)
        
        is_valid = len(errors) == 0
        
        if is_valid:
            logger.info(f"Transcription input validation passed: {input_data.audio_format.value}/{input_data.language}")
        else:
            logger.warning(f"Transcription input validation failed: {len(errors)} errors")
            for error in errors:
                logger.warning(f"  - {error}")
        
        return is_valid, errors
    
    async def _validate_audio_data(self, input_data: TranscriptionInput, options: Dict[str, Any]) -> List[str]:
        """Validate audio data content and size"""
        errors = []
        
        # Check if audio data exists
        if not input_data.audio_data:
            errors.append("Audio data is missing")
            return errors
        
        if len(input_data.audio_data) == 0:
            errors.append("Audio data is empty")
            return errors
        
        # Check audio size limits
        min_size = options.get("min_audio_size_bytes", self.audio_limits["min_size_bytes"])
        max_size_mb = options.get("max_audio_size_mb", self.audio_limits["max_size_mb"])
        max_size = max_size_mb * 1024 * 1024
        
        audio_size = len(input_data.audio_data)
        
        if audio_size < min_size:
            errors.append(
                f"Audio too small: {audio_size} bytes (minimum: {min_size} bytes)"
            )
        
        if audio_size > max_size:
            errors.append(
                f"Audio too large: {audio_size} bytes (maximum: {max_size_mb}MB)"
            )
        
        # Basic audio data validation
        if not self._appears_to_be_audio_data(input_data.audio_data, input_data.audio_format):
            errors.append(f"Data does not appear to be valid {input_data.audio_format.value} audio")
        
        return errors
    
    async def _validate_audio_format(self, input_data: TranscriptionInput) -> List[str]:
        """Validate audio format support"""
        errors = []
        
        if input_data.audio_format not in self.supported_formats:
            supported_names = [f.value for f in self.supported_formats]
            errors.append(
                f"Audio format '{input_data.audio_format.value}' not supported. "
                f"Supported formats: {', '.join(supported_names)}"
            )
        
        return errors
    
    async def _validate_language_support(self, input_data: TranscriptionInput) -> List[str]:
        """Validate language support"""
        errors = []
        
        if input_data.language not in self.supported_languages:
            errors.append(
                f"Language '{input_data.language}' not supported. "
                f"Supported languages: {', '.join(self.supported_languages)}"
            )
        
        return errors
    
    async def _validate_audio_properties(self, input_data: TranscriptionInput) -> List[str]:
        """Validate audio properties like sample rate and channels"""
        errors = []
        
        # Validate sample rate
        if input_data.sample_rate < self.audio_limits["min_sample_rate"]:
            errors.append(
                f"Sample rate too low: {input_data.sample_rate}Hz "
                f"(minimum: {self.audio_limits['min_sample_rate']}Hz)"
            )
        
        if input_data.sample_rate > self.audio_limits["max_sample_rate"]:
            errors.append(
                f"Sample rate too high: {input_data.sample_rate}Hz "
                f"(maximum: {self.audio_limits['max_sample_rate']}Hz)"
            )
        
        # Validate channels
        if input_data.channels not in self.audio_limits["supported_channels"]:
            errors.append(
                f"Unsupported channel count: {input_data.channels} "
                f"(supported: {self.audio_limits['supported_channels']})"
            )
        
        return errors
    
    async def _validate_constraints(self, input_data: TranscriptionInput, options: Dict[str, Any]) -> List[str]:
        """Validate additional constraints"""
        errors = []
        
        # Estimate duration and validate
        estimated_duration = self._estimate_audio_duration(input_data)
        
        min_duration = options.get("min_duration_seconds", self.audio_limits["min_duration_seconds"])
        max_duration = options.get("max_duration_seconds", self.audio_limits["max_duration_seconds"])
        
        if estimated_duration < min_duration:
            errors.append(
                f"Audio too short: {estimated_duration:.1f}s (minimum: {min_duration}s)"
            )
        
        if estimated_duration > max_duration:
            errors.append(
                f"Audio too long: {estimated_duration:.1f}s (maximum: {max_duration}s)"
            )
        
        # Validate metadata constraints
        if input_data.metadata:
            if len(input_data.metadata) > 20:
                errors.append("Too many metadata entries (maximum 20)")
        
        return errors
    
    def _appears_to_be_audio_data(self, audio_data: bytes, audio_format: AudioFormat) -> bool:
        """Basic check if data appears to be valid audio"""
        
        if len(audio_data) < 44:  # Minimum for WAV header
            return False
        
        # Check for common audio file signatures
        if audio_format == AudioFormat.WAV:
            return audio_data[:4] == b'RIFF' and audio_data[8:12] == b'WAVE'
        elif audio_format == AudioFormat.MP3:
            return audio_data[:3] == b'ID3' or audio_data[:2] == b'\xff\xfb'
        elif audio_format == AudioFormat.FLAC:
            return audio_data[:4] == b'fLaC'
        elif audio_format == AudioFormat.OGG:
            return audio_data[:4] == b'OggS'
        else:
            # For other formats, just check if it's not obviously text/binary garbage
            return len(audio_data) > 1000 and not all(b == 0 for b in audio_data[:100])
    
    def _estimate_audio_duration(self, input_data: TranscriptionInput) -> float:
        """Estimate audio duration based on format and properties"""
        
        # For WAV files, try to read duration from header
        if input_data.audio_format == AudioFormat.WAV and len(input_data.audio_data) > 44:
            try:
                # Simple WAV duration calculation
                # bytes_per_sample = bit_depth / 8
                # total_samples = (file_size - 44) / (bytes_per_sample * channels)
                # duration = total_samples / sample_rate
                
                bytes_per_sample = 2  # Assume 16-bit
                data_size = len(input_data.audio_data) - 44  # Subtract header
                total_samples = data_size / (bytes_per_sample * input_data.channels)
                duration = total_samples / input_data.sample_rate
                
                return max(0.1, duration)  # Minimum 0.1 second
                
            except:
                pass
        
        # Fallback: estimate based on file size and format
        # Rough estimates for different formats
        format_bitrates = {
            AudioFormat.WAV: input_data.sample_rate * input_data.channels * 16 / 8,  # Uncompressed
            AudioFormat.FLAC: input_data.sample_rate * input_data.channels * 8 / 8,   # ~50% compression
            AudioFormat.MP3: 128000 / 8,  # Assume 128kbps
            AudioFormat.M4A: 128000 / 8,  # Assume 128kbps
            AudioFormat.OGG: 128000 / 8   # Assume 128kbps
        }
        
        estimated_bitrate = format_bitrates.get(input_data.audio_format, 16000)  # bytes per second
        duration = len(input_data.audio_data) / estimated_bitrate
        
        return max(0.1, min(duration, 7200))  # Between 0.1s and 2 hours
    
    async def validate_audio_quality(self, input_data: TranscriptionInput) -> tuple[bool, List[str], Dict[str, Any]]:
        """
        Validate audio quality for transcription
        Returns: (is_good_quality, warnings, quality_metrics)
        """
        warnings = []
        metrics = {}
        
        # Calculate quality metrics
        audio_size = len(input_data.audio_data)
        estimated_duration = self._estimate_audio_duration(input_data)
        estimated_bitrate = (audio_size * 8) / max(estimated_duration, 0.1)  # bits per second
        
        metrics.update({
            "audio_size_bytes": audio_size,
            "estimated_duration_seconds": estimated_duration,
            "estimated_bitrate_bps": estimated_bitrate,
            "sample_rate": input_data.sample_rate,
            "channels": input_data.channels,
            "format": input_data.audio_format.value
        })
        
        # Quality checks
        if estimated_bitrate < 32000:  # Very low bitrate
            warnings.append("Very low bitrate may result in poor transcription quality")
        
        if input_data.sample_rate < 16000:
            warnings.append("Low sample rate may affect transcription accuracy")
        
        if estimated_duration < 1.0:
            warnings.append("Very short audio may produce incomplete transcription")
        
        if estimated_duration > 1800:  # 30 minutes
            warnings.append("Very long audio may require chunking for optimal processing")
        
        if input_data.channels > 2:
            warnings.append("Multi-channel audio will be mixed down to mono/stereo")
        
        # Determine overall quality
        is_good_quality = (
            len(warnings) <= 1 and
            estimated_bitrate >= 64000 and
            input_data.sample_rate >= 16000 and
            1.0 <= estimated_duration <= 1800
        )
        
        return is_good_quality, warnings, metrics
    
    def get_validation_config(self) -> Dict[str, Any]:
        """Get current validation configuration"""
        return {
            "supported_languages": self.supported_languages,
            "supported_formats": [f.value for f in self.supported_formats],
            "audio_limits": self.audio_limits.copy(),
            "total_supported_languages": len(self.supported_languages),
            "total_supported_formats": len(self.supported_formats)
        }
    
    def update_audio_limits(self, **limits):
        """Update audio validation limits"""
        self.audio_limits.update(limits)
        logger.info(f"Updated audio limits: {limits}")
    
    def add_supported_language(self, language: str):
        """Add supported language"""
        if language not in self.supported_languages:
            self.supported_languages.append(language)
            logger.info(f"Added supported language: {language}")
    
    def add_supported_format(self, audio_format: AudioFormat):
        """Add supported audio format"""
        if audio_format not in self.supported_formats:
            self.supported_formats.append(audio_format)
            logger.info(f"Added supported format: {audio_format.value}")


# Default instance
transcription_validator = TranscriptionValidator()