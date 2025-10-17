"""
Media Type Classifier Service - Single Responsibility: File Type Classification
"""
import os
from src.media_management.domain.enums import MediaType
from src.media_management.config.settings import MediaSettings


class MediaTypeClassifier:
    """
    Service responsible ONLY for classifying media file types.
    
    Single Responsibility: Determine the type of media based on file characteristics.
    """
    
    def __init__(self, settings: MediaSettings):
        self.settings = settings
    
    def classify(self, filename: str) -> MediaType:
        """
        Classify media type based on filename extension.
        
        Args:
            filename: Name of the file to classify
            
        Returns:
            MediaType: The determined media type
            
        Raises:
            ValueError: If file type cannot be determined or is unsupported
        """
        if not filename:
            raise ValueError("Filename is required for classification")
        
        _, ext = os.path.splitext(filename)
        ext = ext.lower()
        
        if not ext:
            raise ValueError("File must have an extension for type classification")
        
        # Classify based on extension
        if self._is_video_extension(ext):
            return MediaType.VIDEO
        elif self._is_audio_extension(ext):
            return MediaType.AUDIO
        elif self._is_text_extension(ext):
            return MediaType.TEXT
        else:
            raise ValueError(
                f"Unsupported file type: {ext}. "
                f"Supported types: {self._get_all_supported_extensions()}"
            )
    
    def _is_video_extension(self, extension: str) -> bool:
        """
        Check if extension is a video type.
        
        Args:
            extension: File extension to check (with dot, e.g., '.mp4')
            
        Returns:
            bool: True if extension is video type
        """
        video_extensions = getattr(self.settings, 'video_extensions', [
            '.mp4', '.mov', '.avi', '.mkv', '.webm', '.wmv', '.flv', '.m4v'
        ])
        return extension in video_extensions
    
    def _is_audio_extension(self, extension: str) -> bool:
        """
        Check if extension is an audio type.
        
        Args:
            extension: File extension to check (with dot, e.g., '.mp3')
            
        Returns:
            bool: True if extension is audio type
        """
        audio_extensions = getattr(self.settings, 'audio_extensions', [
            '.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg', '.wma'
        ])
        return extension in audio_extensions
    
    def _is_text_extension(self, extension: str) -> bool:
        """
        Check if extension is a text/document type.
        
        Args:
            extension: File extension to check (with dot, e.g., '.pdf')
            
        Returns:
            bool: True if extension is text type
        """
        text_extensions = getattr(self.settings, 'text_extensions', [
            '.pdf', '.txt', '.md', '.docx', '.doc', '.rtf'
        ])
        return extension in text_extensions
    
    def _get_all_supported_extensions(self) -> str:
        """
        Get formatted string of all supported extensions.
        
        Returns:
            str: Comma-separated list of supported extensions
        """
        video_exts = getattr(self.settings, 'video_extensions', [])
        audio_exts = getattr(self.settings, 'audio_extensions', [])
        text_exts = getattr(self.settings, 'text_extensions', [])
        
        all_extensions = video_exts + audio_exts + text_exts
        return ', '.join(all_extensions)
    
    def get_processing_requirements(self, media_type: MediaType) -> dict:
        """
        Get processing requirements for a media type.
        
        Args:
            media_type: Type of media
            
        Returns:
            dict: Processing requirements and capabilities
        """
        requirements = {
            'needs_transcription': False,
            'needs_video_processing': False,
            'needs_text_extraction': False,
            'supports_summarization': True,
            'supports_sentiment_analysis': True,
            'supports_topic_modeling': True,
        }
        
        if media_type == MediaType.VIDEO:
            requirements.update({
                'needs_transcription': True,
                'needs_video_processing': True,
            })
        elif media_type == MediaType.AUDIO:
            requirements.update({
                'needs_transcription': True,
            })
        elif media_type == MediaType.TEXT:
            requirements.update({
                'needs_text_extraction': True,
            })
        
        return requirements
    
    def validate_provider_compatibility(self, media_type: MediaType, 
                                       transcription_provider: str = None,
                                       summarization_provider: str = None) -> dict:
        """
        Validate provider compatibility with media type.
        
        Args:
            media_type: Type of media
            transcription_provider: Requested transcription provider
            summarization_provider: Requested summarization provider
            
        Returns:
            dict: Validation results and recommendations
        """
        requirements = self.get_processing_requirements(media_type)
        result = {
            'valid': True,
            'warnings': [],
            'recommendations': [],
        }
        
        # Check transcription provider
        if transcription_provider and not requirements['needs_transcription']:
            result['warnings'].append(
                f"Transcription provider '{transcription_provider}' specified "
                f"but {media_type.value} files don't need transcription"
            )
        
        if requirements['needs_transcription'] and not transcription_provider:
            result['recommendations'].append(
                f"Consider specifying a transcription provider for {media_type.value} files"
            )
        
        # Check summarization provider
        if not summarization_provider:
            result['recommendations'].append(
                "Consider specifying a summarization provider for better results"
            )
        
        return result