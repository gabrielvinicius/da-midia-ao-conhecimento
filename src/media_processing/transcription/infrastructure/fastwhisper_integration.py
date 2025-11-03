"""
FastWhisper Integration - Connects FastWhisper provider to transcription pipeline
"""
import structlog
from typing import Dict, Any, Optional
from uuid import UUID

from src.shared.infrastructure.unified_providers import provider_registry
from .providers.fastwhisper_provider import FastWhisperProvider
from src.shared.config.unified_settings import get_settings

logger = structlog.get_logger(__name__)

class FastWhisperIntegration:
    """Integration class for FastWhisper in transcription pipeline"""
    
    def __init__(self):
        self.settings = get_settings()
        self._provider: Optional[FastWhisperProvider] = None
        self._initialize_provider()
    
    def _initialize_provider(self):
        """Initialize FastWhisper provider"""
        try:
            # Get FastWhisper configuration
            config = self._get_fastwhisper_config()
            
            # Create provider instance
            self._provider = FastWhisperProvider(config)
            
            # Register with global provider registry
            provider_registry.register(self._provider)
            
            logger.info("FastWhisper provider initialized and registered", 
                       model_size=config.get('model_size'),
                       device=config.get('device'))
            
        except Exception as e:
            logger.error("Failed to initialize FastWhisper provider", error=str(e))
            raise
    
    def _get_fastwhisper_config(self) -> Dict[str, Any]:
        """Get FastWhisper configuration from settings"""
        return {
            # Model configuration
            'model_size': self.settings.get_module_config('transcription').get('fastwhisper_model_size', 'base'),
            'device': self.settings.get_module_config('transcription').get('fastwhisper_device', 'auto'),
            'compute_type': self.settings.get_module_config('transcription').get('fastwhisper_compute_type', 'int8'),
            
            # Performance settings
            'cache_dir': self.settings.get_module_config('transcription').get('model_cache_dir'),
            'local_files_only': self.settings.get_module_config('transcription').get('local_files_only', False),
            
            # Transcription defaults
            'beam_size': 5,
            'best_of': 5,
            'patience': 1.0,
            'length_penalty': 1.0,
            'repetition_penalty': 1.0,
            'temperature': [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
            'compression_ratio_threshold': 2.4,
            'log_prob_threshold': -1.0,
            'no_speech_threshold': 0.6,
            'condition_on_previous_text': True,
            'word_timestamps': True,
            'prepend_punctuations': "\"'([{-",
            'append_punctuations': "\"'.!?:"
        }
    
    async def transcribe_audio(
        self, 
        audio_data: bytes, 
        language: str = 'auto',
        **options
    ) -> Dict[str, Any]:
        """Transcribe audio using FastWhisper"""
        if not self._provider:
            raise RuntimeError("FastWhisper provider not initialized")
        
        try:
            # Process with FastWhisper
            result = await self._provider.process(
                audio_data, 
                language=language,
                **options
            )
            
            if result.success:
                return result.data
            else:
                raise RuntimeError(f"Transcription failed: {result.error}")
                
        except Exception as e:
            logger.error("FastWhisper transcription failed", error=str(e))
            raise
    
    async def transcribe_from_video_pipeline(
        self, 
        audio_data: bytes, 
        media_id: UUID,
        language: str = 'auto'
    ) -> Dict[str, Any]:
        """Transcribe audio extracted from video processing pipeline"""
        try:
            logger.info("Starting transcription from video pipeline", 
                       media_id=str(media_id), 
                       language=language,
                       audio_size=len(audio_data))
            
            # Optimize settings for video-extracted audio
            video_options = {
                'task': 'transcribe',
                'beam_size': 5,
                'word_timestamps': True,
                'condition_on_previous_text': True,
                'suppress_blank': True
            }
            
            result = await self.transcribe_audio(
                audio_data, 
                language=language,
                **video_options
            )
            
            # Add video pipeline specific metadata
            result['source'] = 'video_pipeline'
            result['media_id'] = str(media_id)
            
            logger.info("Video pipeline transcription completed", 
                       media_id=str(media_id),
                       text_length=len(result.get('text', '')),
                       detected_language=result.get('language'))
            
            return result
            
        except Exception as e:
            logger.error("Video pipeline transcription failed", 
                        media_id=str(media_id), 
                        error=str(e))
            raise
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get FastWhisper provider information"""
        if not self._provider:
            return {"status": "not_initialized"}
        
        return {
            "status": "initialized",
            "capabilities": self._provider.get_capabilities(),
            "config": self._get_fastwhisper_config()
        }
    
    async def health_check(self) -> bool:
        """Check FastWhisper provider health"""
        if not self._provider:
            return False
        
        return await self._provider.health_check()

# Global integration instance
fastwhisper_integration = FastWhisperIntegration()

# Convenience functions
async def transcribe_with_fastwhisper(
    audio_data: bytes, 
    language: str = 'auto',
    **options
) -> Dict[str, Any]:
    """Convenience function for FastWhisper transcription"""
    return await fastwhisper_integration.transcribe_audio(audio_data, language, **options)

async def transcribe_from_video(
    audio_data: bytes, 
    media_id: UUID,
    language: str = 'auto'
) -> Dict[str, Any]:
    """Convenience function for video pipeline transcription"""
    return await fastwhisper_integration.transcribe_from_video_pipeline(audio_data, media_id, language)
