"""
Video to Transcription Pipeline Integration
Connects video processing with transcription using FastWhisper
"""
import structlog
from typing import Dict, Any, Optional
from uuid import UUID

from ..application.services.video_orchestrator import video_orchestrator
from src.transcription.application.services.fastwhisper_service import fastwhisper_service
from src.shared.events.unified_events import publish_processing_completed, publish_processing_failed

logger = structlog.get_logger(__name__)

class VideoTranscriptionPipeline:
    """Orchestrates the video → audio extraction → transcription pipeline"""
    
    def __init__(self):
        self.video_orchestrator = video_orchestrator
        self.transcription_service = fastwhisper_service
    
    async def process_video_to_transcription(
        self,
        video_data: bytes,
        filename: str,
        media_id: UUID,
        user_id: UUID,
        language: str = 'auto',
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Complete pipeline: Video → Audio Extraction → Transcription
        """
        options = options or {}
        
        try:
            logger.info("Starting video to transcription pipeline", 
                       media_id=str(media_id),
                       filename=filename,
                       language=language)
            
            # Step 1: Process video (extract audio + thumbnail)
            logger.info("Step 1: Processing video", media_id=str(media_id))
            
            video_result = await self.video_orchestrator.orchestrate(
                video_data,
                entity_id=str(media_id),
                filename=filename,
                user_id=str(user_id),
                options={
                    'extract_audio': True,
                    'generate_thumbnail': options.get('generate_thumbnail', True),
                    'audio_format': 'wav',
                    'thumbnail_size': options.get('thumbnail_size', 'medium'),
                    **options
                }
            )
            
            if not video_result.get('success', False):
                raise RuntimeError("Video processing failed")
            
            # Get extracted audio
            extracted_audio = video_result.get('extracted_audio')
            if not extracted_audio:
                raise RuntimeError("Audio extraction failed - no audio data")
            
            logger.info("Step 1 completed: Audio extracted", 
                       media_id=str(media_id),
                       audio_size=len(extracted_audio))
            
            # Step 2: Transcribe extracted audio
            logger.info("Step 2: Transcribing audio", media_id=str(media_id))
            
            transcription_result = await self.transcription_service.transcribe_from_video(
                extracted_audio,
                media_id,
                language=language,
                word_timestamps=options.get('word_timestamps', True),
                task=options.get('transcription_task', 'transcribe')
            )
            
            logger.info("Step 2 completed: Transcription done", 
                       media_id=str(media_id),
                       text_length=len(transcription_result.get('text', '')))
            
            # Step 3: Compile complete results
            complete_result = {
                'media_id': str(media_id),
                'user_id': str(user_id),
                'filename': filename,
                'pipeline': 'video_to_transcription',
                'success': True,
                
                # Video processing results
                'video_processing': {
                    'success': video_result.get('success'),
                    'audio_extraction': video_result.get('audio_extraction'),
                    'thumbnail_generation': video_result.get('thumbnail_generation'),
                    'video_metadata': video_result.get('video_metadata'),
                    'processing_steps': video_result.get('processing_steps')
                },
                
                # Transcription results
                'transcription': {
                    'text': transcription_result.get('text', ''),
                    'language': transcription_result.get('language'),
                    'confidence': transcription_result.get('language_probability'),
                    'duration': transcription_result.get('duration'),
                    'segments': transcription_result.get('segments', []),
                    'model_info': transcription_result.get('model_info')
                },
                
                # Pipeline metadata
                'pipeline_info': {
                    'steps_completed': ['video_processing', 'audio_extraction', 'transcription'],
                    'next_suggested_steps': self._suggest_next_steps(transcription_result, options),
                    'total_processing_time': None,  # Would be calculated in real implementation
                    'original_video_size': len(video_data),
                    'extracted_audio_size': len(extracted_audio),
                    'text_length': len(transcription_result.get('text', ''))
                }
            }
            
            # Publish success event
            await publish_processing_completed(
                entity_type="video_transcription_pipeline",
                entity_id=str(media_id),
                user_id=str(user_id),
                **complete_result['pipeline_info']
            )
            
            logger.info("Video to transcription pipeline completed successfully", 
                       media_id=str(media_id),
                       text_length=len(transcription_result.get('text', '')),
                       language=transcription_result.get('language'))
            
            return complete_result
            
        except Exception as e:
            # Publish failure event
            await publish_processing_failed(
                entity_type="video_transcription_pipeline",
                entity_id=str(media_id),
                user_id=str(user_id),
                error=str(e)
            )
            
            logger.error("Video to transcription pipeline failed", 
                        media_id=str(media_id),
                        error=str(e))
            raise
    
    def _suggest_next_steps(self, transcription_result: Dict[str, Any], options: Dict[str, Any]) -> list:
        """Suggest next pipeline steps based on results and options"""
        next_steps = []
        
        # If we have text, suggest summarization
        if transcription_result.get('text', '').strip():
            if options.get('enable_summarization', True):
                next_steps.append('summarization')
            
            if options.get('enable_sentiment_analysis', False):
                next_steps.append('sentiment_analysis')
            
            if options.get('enable_topic_modeling', False):
                next_steps.append('topic_modeling')
        
        return next_steps
    
    async def extract_audio_only(
        self,
        video_data: bytes,
        filename: str,
        media_id: UUID,
        audio_format: str = 'wav'
    ) -> bytes:
        """Extract audio only from video (for other use cases)"""
        try:
            audio_data = await self.video_orchestrator.extract_audio_for_transcription(
                video_data, 
                filename
            )
            
            logger.info("Audio extracted from video", 
                       media_id=str(media_id),
                       audio_size=len(audio_data))
            
            return audio_data
            
        except Exception as e:
            logger.error("Audio extraction failed", 
                        media_id=str(media_id),
                        error=str(e))
            raise
    
    async def transcribe_audio_only(
        self,
        audio_data: bytes,
        media_id: UUID,
        language: str = 'auto',
        **options
    ) -> Dict[str, Any]:
        """Transcribe audio only (already extracted)"""
        try:
            result = await self.transcription_service.transcribe_from_video(
                audio_data,
                media_id,
                language=language,
                **options
            )
            
            logger.info("Audio transcribed", 
                       media_id=str(media_id),
                       text_length=len(result.get('text', '')))
            
            return result
            
        except Exception as e:
            logger.error("Audio transcription failed", 
                        media_id=str(media_id),
                        error=str(e))
            raise

# Global pipeline instance
video_transcription_pipeline = VideoTranscriptionPipeline()

# Convenience functions
async def process_video_file_to_text(
    video_data: bytes,
    filename: str,
    media_id: UUID,
    user_id: UUID,
    language: str = 'auto',
    **options
) -> Dict[str, Any]:
    """Convenience function for complete video → text pipeline"""
    return await video_transcription_pipeline.process_video_to_transcription(
        video_data, filename, media_id, user_id, language, options
    )