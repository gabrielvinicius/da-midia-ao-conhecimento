"""
FastWhisper Provider - High-performance Whisper implementation
"""
import structlog
from typing import Dict, Any, List, Optional
import tempfile
import os
from pathlib import Path

from src.shared.infrastructure.unified_providers import TranscriptionProvider, ProviderResult

logger = structlog.get_logger(__name__)

class FastWhisperProvider(TranscriptionProvider):
    """FastWhisper provider for high-performance speech recognition"""
    
    def __init__(self, config: Dict = None):
        super().__init__("fastwhisper", config)
        self.config = config or {}
        self._initialize_fastwhisper()
    
    def _initialize_fastwhisper(self):
        """Initialize FastWhisper model"""
        try:
            import faster_whisper
            
            # Model configuration
            model_size = self.config.get('model_size', 'base')
            device = self.config.get('device', 'auto')  # auto, cpu, cuda
            compute_type = self.config.get('compute_type', 'int8')  # int8, float16, float32
            
            self.logger.info("Initializing FastWhisper model", 
                           model_size=model_size, 
                           device=device,
                           compute_type=compute_type)
            
            # Initialize model
            self.model = faster_whisper.WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
                download_root=self.config.get('cache_dir'),
                local_files_only=self.config.get('local_files_only', False)
            )
            
            # Model configuration
            self.supported_languages = {
                'en': 'English', 'es': 'Spanish', 'fr': 'French', 'de': 'German',
                'it': 'Italian', 'pt': 'Portuguese', 'ru': 'Russian', 'ja': 'Japanese',
                'ko': 'Korean', 'zh': 'Chinese', 'ar': 'Arabic', 'hi': 'Hindi',
                'auto': 'Auto-detect'
            }
            
            self.logger.info("FastWhisper model initialized successfully")
            
        except ImportError:
            self.logger.error("faster-whisper package not installed")
            raise ImportError("faster-whisper package is required. Install with: pip install faster-whisper")
        except Exception as e:
            self.logger.error("Failed to initialize FastWhisper model", error=str(e))
            raise
    
    async def _execute(self, audio_data: bytes, **kwargs) -> Dict[str, Any]:
        """Execute transcription using FastWhisper"""
        language = kwargs.get('language', 'auto')
        
        try:
            self.logger.info("Starting FastWhisper transcription", 
                           language=language, 
                           audio_size=len(audio_data))
            
            # Validate language
            if language not in self.supported_languages:
                language = 'auto'
                self.logger.warning("Unsupported language, using auto-detect", 
                                  requested_language=kwargs.get('language'))
            
            # Save audio to temporary file
            audio_result = await self._transcribe_audio_data(audio_data, language, **kwargs)
            
            self.logger.info("FastWhisper transcription completed", 
                           text_length=len(audio_result.get('text', '')),
                           detected_language=audio_result.get('language'))
            
            return audio_result
            
        except Exception as e:
            self.logger.error("FastWhisper transcription failed", error=str(e))
            raise
    
    async def _transcribe_audio_data(self, audio_data: bytes, language: str, **kwargs) -> Dict[str, Any]:
        """Transcribe audio data using FastWhisper"""
        # Create temporary file for audio
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_file.write(audio_data)
            temp_path = temp_file.name
        
        try:
            # Transcription options
            options = {
                'language': None if language == 'auto' else language,
                'task': kwargs.get('task', 'transcribe'),  # transcribe or translate
                'beam_size': kwargs.get('beam_size', 5),
                'best_of': kwargs.get('best_of', 5),
                'patience': kwargs.get('patience', 1.0),
                'length_penalty': kwargs.get('length_penalty', 1.0),
                'repetition_penalty': kwargs.get('repetition_penalty', 1.0),
                'no_repeat_ngram_size': kwargs.get('no_repeat_ngram_size', 0),
                'temperature': kwargs.get('temperature', [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]),
                'compression_ratio_threshold': kwargs.get('compression_ratio_threshold', 2.4),
                'log_prob_threshold': kwargs.get('log_prob_threshold', -1.0),
                'no_speech_threshold': kwargs.get('no_speech_threshold', 0.6),
                'condition_on_previous_text': kwargs.get('condition_on_previous_text', True),
                'prompt_reset_on_temperature': kwargs.get('prompt_reset_on_temperature', 0.5),
                'initial_prompt': kwargs.get('initial_prompt'),
                'prefix': kwargs.get('prefix'),
                'suppress_blank': kwargs.get('suppress_blank', True),
                'suppress_tokens': kwargs.get('suppress_tokens', [-1]),
                'without_timestamps': kwargs.get('without_timestamps', False),
                'max_initial_timestamp': kwargs.get('max_initial_timestamp', 1.0),
                'word_timestamps': kwargs.get('word_timestamps', False),
                'prepend_punctuations': kwargs.get('prepend_punctuations', "\"'([{-"),
                'append_punctuations': kwargs.get('append_punctuations', "\"'.!?:"),
            }
            
            # Remove None values
            options = {k: v for k, v in options.items() if v is not None}
            
            # Perform transcription
            segments, info = self.model.transcribe(temp_path, **options)
            
            # Process results
            text_segments = []
            full_text = ""
            
            for segment in segments:
                segment_data = {
                    'id': segment.id,
                    'start': segment.start,
                    'end': segment.end,
                    'text': segment.text.strip(),
                    'tokens': segment.tokens if hasattr(segment, 'tokens') else [],
                    'temperature': segment.temperature if hasattr(segment, 'temperature') else None,
                    'avg_logprob': segment.avg_logprob if hasattr(segment, 'avg_logprob') else None,
                    'compression_ratio': segment.compression_ratio if hasattr(segment, 'compression_ratio') else None,
                    'no_speech_prob': segment.no_speech_prob if hasattr(segment, 'no_speech_prob') else None,
                }
                
                # Add word-level timestamps if available
                if hasattr(segment, 'words') and segment.words:
                    segment_data['words'] = [
                        {
                            'word': word.word,
                            'start': word.start,
                            'end': word.end,
                            'probability': word.probability if hasattr(word, 'probability') else None
                        }
                        for word in segment.words
                    ]
                
                text_segments.append(segment_data)
                full_text += segment.text
            
            # Compile results
            result = {
                'text': full_text.strip(),
                'language': info.language,
                'language_probability': info.language_probability,
                'duration': info.duration,
                'duration_after_vad': info.duration_after_vad if hasattr(info, 'duration_after_vad') else info.duration,
                'all_language_probs': info.all_language_probs if hasattr(info, 'all_language_probs') else None,
                'segments': text_segments,
                'model_info': {
                    'model_size': self.config.get('model_size', 'base'),
                    'device': self.config.get('device', 'auto'),
                    'compute_type': self.config.get('compute_type', 'int8')
                }
            }
            
            return result
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get FastWhisper provider capabilities"""
        return {
            "provider": self.provider_name,
            "type": self.provider_type.value,
            "supports_async": True,
            "supported_languages": list(self.supported_languages.keys()),
            "language_names": self.supported_languages,
            "features": {
                "word_timestamps": True,
                "language_detection": True,
                "translation": True,
                "streaming": False,
                "batch_processing": True,
                "punctuation": True,
                "speaker_diarization": False
            },
            "audio_formats": [
                "wav", "mp3", "m4a", "ogg", "flac", "aac"
            ],
            "max_audio_length": 3600,  # 1 hour in seconds
            "model_sizes": ["tiny", "base", "small", "medium", "large-v1", "large-v2", "large-v3"],
            "current_model": self.config.get('model_size', 'base')
        }
    
    async def health_check(self) -> bool:
        """Check if FastWhisper provider is healthy"""
        try:
            # Create a small test audio (1 second of silence)
            import numpy as np
            sample_rate = 16000
            duration = 1
            silence = np.zeros(sample_rate * duration, dtype=np.float32)
            
            # Convert to bytes (simple WAV format)
            import wave
            import io
            
            buffer = io.BytesIO()
            with wave.open(buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes((silence * 32767).astype(np.int16).tobytes())
            
            test_audio = buffer.getvalue()
            
            # Try to transcribe
            result = await self._execute(test_audio, language='en')
            
            # Health check passes if we get a result (even if empty text)
            return isinstance(result, dict) and 'text' in result
            
        except Exception as e:
            self.logger.error("FastWhisper health check failed", error=str(e))
            return False
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages"""
        return list(self.supported_languages.keys())
    
    def estimate_processing_time(self, audio_duration: float) -> float:
        """Estimate processing time based on audio duration"""
        # FastWhisper is typically 10-20x faster than real-time
        # This depends on model size and hardware
        model_size = self.config.get('model_size', 'base')
        
        speed_multipliers = {
            'tiny': 30,    # 30x real-time
            'base': 20,    # 20x real-time
            'small': 15,   # 15x real-time
            'medium': 10,  # 10x real-time
            'large-v1': 5, # 5x real-time
            'large-v2': 5,
            'large-v3': 5
        }
        
        multiplier = speed_multipliers.get(model_size, 15)
        return audio_duration / multiplier
