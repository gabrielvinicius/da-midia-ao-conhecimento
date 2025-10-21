"""
FastWhisper Service - Main service for FastWhisper transcription
"""
import structlog
from typing import Dict, Any, Optional
from uuid import UUID

from src.shared.application.unified_services import UnifiedProcessor
from ..infrastructure.fastwhisper_integration import fastwhisper_integration

logger = structlog.get_logger(__name__)

class FastWhisperService(UnifiedProcessor):
    """FastWhisper transcription service integrated with unified architecture"""
    
    def __init__(self):
        super().__init__("fastwhisper_transcription")
        self.integration = fastwhisper_integration
    
    async def _do_process(self, audio_data: bytes, **kwargs) -> Dict[str, Any]:
        """Process audio using FastWhisper"""
        try:
            language = kwargs.get('language', 'auto')
            media_id = kwargs.get('media_id')
            
            self.logger.info("Starting FastWhisper transcription service", 
                           language=language, 
                           audio_size=len(audio_data),
                           media_id=media_id)
            
            # Use integration for transcription
            if media_id:
                # Use video pipeline specific transcription
                result = await self.integration.transcribe_from_video_pipeline(
                    audio_data, 
                    UUID(media_id) if isinstance(media_id, str) else media_id,
                    language
                )
            else:
                # Use general transcription
                result = await self.integration.transcribe_audio(
                    audio_data, 
                    language,
                    **kwargs
                )
            
            # Add service metadata
            result.update({
                'service': 'fastwhisper_service',
                'processing_info': {
                    'audio_size_bytes': len(audio_data),
                    'language_requested': language,
                    'language_detected': result.get('language'),
                    'confidence': result.get('language_probability'),
                    'duration': result.get('duration'),
                    'segments_count': len(result.get('segments', []))
                }
            })
            
            self.logger.info("FastWhisper transcription service completed", 
                           text_length=len(result.get('text', '')),
                           language_detected=result.get('language'),
                           segments_count=len(result.get('segments', [])))
            
            return result
            
        except Exception as e:
            self.logger.error("FastWhisper service failed", error=str(e))
            raise
    
    async def transcribe_from_video(
        self, 
        audio_data: bytes, 
        media_id: UUID, 
        language: str = 'auto',
        **options
    ) -> Dict[str, Any]:
        """Transcribe audio extracted from video"""
        return await self.process(
            audio_data,
            media_id=media_id,
            language=language,
            **options
        )
    
    async def transcribe_audio_file(
        self, 
        audio_data: bytes, 
        language: str = 'auto',
        **options
    ) -> Dict[str, Any]:
        """Transcribe standalone audio file"""
        return await self.process(
            audio_data,
            language=language,
            **options
        )
    
    async def get_provider_status(self) -> Dict[str, Any]:
        """Get FastWhisper provider status"""
        try:
            info = self.integration.get_provider_info()
            health = await self.integration.health_check()
            
            return {
                'provider': 'fastwhisper',
                'status': 'healthy' if health else 'unhealthy',
                'health_check': health,
                'info': info
            }
        except Exception as e:
            return {
                'provider': 'fastwhisper',
                'status': 'error',
                'error': str(e)
            }
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get supported languages"""
        try:
            info = self.integration.get_provider_info()
            capabilities = info.get('capabilities', {})
            return capabilities.get('language_names', {})
        except:
            return {}
    
    def estimate_processing_time(self, audio_duration: float, model_size: str = 'base') -> float:
        """Estimate processing time"""
        speed_multipliers = {
            'tiny': 30,    # 30x real-time
            'base': 20,    # 20x real-time  
            'small': 15,   # 15x real-time
            'medium': 10,  # 10x real-time
            'large-v1': 5, # 5x real-time
            'large-v2': 5,
            'large-v3': 5
        }
        
        multiplier = speed_multipliers.get(model_size, 20)
        return audio_duration / multiplier

# Global service instance
fastwhisper_service = FastWhisperService()