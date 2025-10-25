# src/video_processing/infrastructure/video_audio_extractor.py
import structlog
from typing import Optional, Dict, Any
import tempfile
import os
from pathlib import Path
import subprocess
import asyncio
import moviepy.editor as mp
import io
import wave

class FFmpegVideoAudioExtractor:
    """Concrete implementation of IVideoAudioExtractor using FFmpeg and MoviePy as fallback."""

    def __init__(self):
        self.supported_formats = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm'}

    async def extract_audio(self, video_data: bytes, filename: str, output_format: str = 'wav') -> Dict[str, Any]:
        logger.info(
            "ffmpeg_video_audio_extractor.extracting_audio",
            filename=filename,
            output_format=output_format
        )
        try:
            # Check if file format is supported
            file_ext = Path(filename).suffix.lower()
            if file_ext not in self.supported_formats:
                raise ValueError(f"Unsupported video format: {file_ext}")
            
            # Extract audio using FFmpeg
            audio_data = await self._extract_with_ffmpeg(video_data, filename, output_format)
            
            # Get audio metadata
            metadata = await self._get_audio_metadata(audio_data, output_format)
            
            return {
                'audio_data': audio_data,
                'audio_format': output_format,
                'original_video_size': len(video_data),
                'extracted_audio_size': len(audio_data),
                'metadata': metadata,
                'success': True
            }
            
        except Exception as e:
            logger.error("Audio extraction failed", error=str(e), filename=filename)
            raise

    async def _extract_with_ffmpeg(self, video_data: bytes, filename: str, output_format: str) -> bytes:
        """Extract audio using FFmpeg."""
        # Create temporary files
        with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix, delete=False) as video_temp:
            video_temp.write(video_data)
            video_temp_path = video_temp.name
        
        with tempfile.NamedTemporaryFile(suffix=f'.{output_format}', delete=False) as audio_temp:
            audio_temp_path = audio_temp.name
        
        try:
            cmd = [
                'ffmpeg', '-y',
                '-i', video_temp_path,
                '-vn',
                '-acodec', 'pcm_s16le' if output_format == 'wav' else 'mp3',
                '-ar', '16000',
                '-ac', '1',
                audio_temp_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"FFmpeg failed: {stderr.decode()}", stdout=stdout.decode(), stderr=stderr.decode())
                raise RuntimeError(f"FFmpeg failed: {stderr.decode()}")
            
            with open(audio_temp_path, 'rb') as f:
                audio_data = f.read()
            
            return audio_data
            
        finally:
            if os.path.exists(video_temp_path):
                os.unlink(video_temp_path)
            if os.path.exists(audio_temp_path):
                os.unlink(audio_temp_path)
    
    async def _get_audio_metadata(self, audio_data: bytes, audio_format: str) -> Dict[str, Any]:
        """Get metadata from extracted audio."""
        metadata = {'size_bytes': len(audio_data), 'format': audio_format}
        
        if audio_format == 'wav':
            try:
                with wave.open(io.BytesIO(audio_data), 'rb') as wav_file:
                    metadata.update({
                        'channels': wav_file.getnchannels(),
                        'sample_rate': wav_file.getframerate(),
                        'sample_width': wav_file.getsampwidth(),
                        'duration_seconds': wav_file.getnframes() / wav_file.getframerate()
                    })
            except Exception as e:
                logger.warning("Failed to extract detailed WAV metadata", error=str(e))
        # TODO: Adicionar lógica para outros formatos como MP3
        
        return metadata
