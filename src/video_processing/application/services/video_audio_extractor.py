"""
Video Audio Extractor - Essential service for video processing pipeline
"""
import structlog
from typing import Optional, Dict, Any
import tempfile
import os
from pathlib import Path

from src.shared.application.unified_services import UnifiedProcessor

logger = structlog.get_logger(__name__)

class VideoAudioExtractor(UnifiedProcessor):
    """Extract audio from video files - essential for video pipeline"""
    
    def __init__(self):
        super().__init__("video_audio_extraction")
        self.supported_formats = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm'}
    
    async def _do_process(self, video_data: bytes, **kwargs) -> Dict[str, Any]:
        """Extract audio from video data"""
        filename = kwargs.get('filename', 'video.mp4')
        output_format = kwargs.get('audio_format', 'wav')
        
        try:
            # Check if file format is supported
            file_ext = Path(filename).suffix.lower()
            if file_ext not in self.supported_formats:
                raise ValueError(f"Unsupported video format: {file_ext}")
            
            # Extract audio using FFmpeg (simplified implementation)
            audio_data = await self._extract_with_ffmpeg(video_data, filename, output_format)
            
            # Get audio metadata
            metadata = await self._get_audio_metadata(audio_data)
            
            return {
                'audio_data': audio_data,
                'audio_format': output_format,
                'original_video_size': len(video_data),
                'extracted_audio_size': len(audio_data),
                'metadata': metadata,
                'success': True
            }
            
        except Exception as e:
            self.logger.error("Audio extraction failed", error=str(e), filename=filename)
            raise
    
    async def _extract_with_ffmpeg(self, video_data: bytes, filename: str, output_format: str) -> bytes:
        """Extract audio using FFmpeg"""
        try:
            # Try importing subprocess for FFmpeg
            import subprocess
            import asyncio
            
            # Create temporary files
            with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix, delete=False) as video_temp:
                video_temp.write(video_data)
                video_temp_path = video_temp.name
            
            with tempfile.NamedTemporaryFile(suffix=f'.{output_format}', delete=False) as audio_temp:
                audio_temp_path = audio_temp.name
            
            try:
                # FFmpeg command to extract audio
                cmd = [
                    'ffmpeg', '-y',  # -y to overwrite output files
                    '-i', video_temp_path,  # input video
                    '-vn',  # no video
                    '-acodec', 'pcm_s16le' if output_format == 'wav' else 'mp3',  # audio codec
                    '-ar', '16000',  # sample rate
                    '-ac', '1',  # mono channel
                    audio_temp_path  # output audio
                ]
                
                # Run FFmpeg
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    raise RuntimeError(f"FFmpeg failed: {stderr.decode()}")
                
                # Read extracted audio
                with open(audio_temp_path, 'rb') as f:
                    audio_data = f.read()
                
                return audio_data
                
            finally:
                # Cleanup temp files
                if os.path.exists(video_temp_path):
                    os.unlink(video_temp_path)
                if os.path.exists(audio_temp_path):
                    os.unlink(audio_temp_path)
                    
        except ImportError:
            self.logger.warning("FFmpeg not available, using fallback method")
            return await self._fallback_audio_extraction(video_data)
        except Exception as e:
            self.logger.error("FFmpeg extraction failed", error=str(e))
            return await self._fallback_audio_extraction(video_data)
    
    async def _fallback_audio_extraction(self, video_data: bytes) -> bytes:
        """Fallback audio extraction without FFmpeg"""
        try:
            # Try using moviepy as fallback
            import moviepy.editor as mp
            import io
            
            # Write video to temporary file
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
                temp_file.write(video_data)
                temp_path = temp_file.name
            
            try:
                # Extract audio using moviepy
                video = mp.VideoFileClip(temp_path)
                audio = video.audio
                
                # Write audio to temporary file
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as audio_temp:
                    audio_temp_path = audio_temp.name
                
                audio.write_audiofile(audio_temp_path, logger=None)
                
                # Read audio data
                with open(audio_temp_path, 'rb') as f:
                    audio_data = f.read()
                
                # Cleanup
                audio.close()
                video.close()
                
                if os.path.exists(audio_temp_path):
                    os.unlink(audio_temp_path)
                
                return audio_data
                
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except ImportError:
            self.logger.error("Neither FFmpeg nor moviepy available for audio extraction")
            # Return empty audio data as last resort
            return b''
        except Exception as e:
            self.logger.error("Fallback audio extraction failed", error=str(e))
            return b''
    
    async def _get_audio_metadata(self, audio_data: bytes) -> Dict[str, Any]:
        """Get metadata from extracted audio"""
        try:
            # Basic metadata
            metadata = {
                'size_bytes': len(audio_data),
                'format': 'wav',  # Assuming wav output
                'channels': 1,    # Mono
                'sample_rate': 16000
            }
            
            # Try to get more detailed metadata if possible
            try:
                import wave
                import io
                
                # Try to read as WAV file
                with wave.open(io.BytesIO(audio_data), 'rb') as wav_file:
                    metadata.update({
                        'channels': wav_file.getnchannels(),
                        'sample_rate': wav_file.getframerate(),
                        'sample_width': wav_file.getsampwidth(),
                        'duration_seconds': wav_file.getnframes() / wav_file.getframerate()
                    })
            except:
                # If we can't read detailed metadata, use defaults
                pass
            
            return metadata
            
        except Exception as e:
            self.logger.warning("Failed to extract audio metadata", error=str(e))
            return {'size_bytes': len(audio_data)}
    
    def is_supported_format(self, filename: str) -> bool:
        """Check if video format is supported"""
        file_ext = Path(filename).suffix.lower()
        return file_ext in self.supported_formats
    
    def get_supported_formats(self) -> list:
        """Get list of supported video formats"""
        return list(self.supported_formats)