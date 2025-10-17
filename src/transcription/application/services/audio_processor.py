# src/transcription/application/services/audio_processor.py
"""
Audio processing service implementation - SRP compliance.
"""
import asyncio
import numpy as np
from typing import Dict, Any
import magic
import struct

from src.transcription.domain.interfaces import AudioProcessor


class DefaultAudioProcessor(AudioProcessor):
    """
    Default implementation of audio processing.
    Follows SRP - only responsible for audio processing operations.
    """
    
    def __init__(
        self,
        target_sample_rate: int = 16000,
        max_file_size: int = 100 * 1024 * 1024,  # 100MB
        min_duration: float = 0.1,  # 0.1 seconds
        max_duration: float = 3600.0  # 1 hour
    ):
        self.target_sample_rate = target_sample_rate
        self.max_file_size = max_file_size
        self.min_duration = min_duration
        self.max_duration = max_duration
    
    async def validate_audio(self, audio_data: bytes) -> bool:
        """Validate audio data."""
        try:
            # Check file size
            if len(audio_data) > self.max_file_size:
                return False
            
            if len(audio_data) < 100:  # Too small to be valid audio
                return False
            
            # Check MIME type
            mime_type = magic.from_buffer(audio_data, mime=True)
            valid_audio_types = [
                'audio/mpeg', 'audio/wav', 'audio/x-wav', 'audio/mp4',
                'audio/aac', 'audio/ogg', 'audio/flac', 'audio/x-flac',
                'video/mp4', 'video/mpeg', 'video/quicktime', 'video/x-msvideo'
            ]
            
            if mime_type not in valid_audio_types:
                return False
            
            # Try to extract basic info
            info = await self.extract_audio_info(audio_data)
            duration = info.get("duration", 0.0)
            
            # Check duration constraints
            if duration < self.min_duration or duration > self.max_duration:
                return False
            
            return True
            
        except Exception:
            return False
    
    async def extract_audio_info(self, audio_data: bytes) -> Dict[str, Any]:
        """Extract audio metadata using FFprobe."""
        try:
            # Use FFprobe to get audio information
            command = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                '-i', 'pipe:0'
            ]
            
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate(input=audio_data)
            
            if process.returncode != 0:
                # Fallback to basic analysis
                return await self._analyze_audio_basic(audio_data)
            
            import json
            probe_data = json.loads(stdout.decode())
            
            # Extract relevant information
            format_info = probe_data.get('format', {})
            audio_streams = [
                stream for stream in probe_data.get('streams', [])
                if stream.get('codec_type') == 'audio'
            ]
            
            if audio_streams:
                audio_stream = audio_streams[0]
                return {
                    "duration": float(format_info.get('duration', 0.0)),
                    "sample_rate": int(audio_stream.get('sample_rate', 0)),
                    "channels": int(audio_stream.get('channels', 0)),
                    "codec": audio_stream.get('codec_name', 'unknown'),
                    "bit_rate": int(format_info.get('bit_rate', 0)),
                    "format": format_info.get('format_name', 'unknown'),
                    "size": int(format_info.get('size', len(audio_data)))
                }
            else:
                return await self._analyze_audio_basic(audio_data)
            
        except Exception:
            return await self._analyze_audio_basic(audio_data)
    
    async def normalize_audio(self, audio_data: bytes) -> bytes:
        """Normalize audio for transcription."""
        try:
            # Convert to target format using FFmpeg
            command = [
                'ffmpeg',
                '-i', 'pipe:0',
                '-f', 'wav',
                '-ac', '1',  # Mono
                '-ar', str(self.target_sample_rate),  # Target sample rate
                '-acodec', 'pcm_s16le',  # PCM 16-bit
                '-loglevel', 'error',
                'pipe:1'
            ]
            
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate(input=audio_data)
            
            if process.returncode != 0:
                # If normalization fails, return original
                return audio_data
            
            return stdout
            
        except Exception:
            # If normalization fails, return original
            return audio_data
    
    async def extract_audio_from_video(self, video_data: bytes) -> bytes:
        """Extract audio from video."""
        try:
            # Extract audio using FFmpeg
            command = [
                'ffmpeg',
                '-i', 'pipe:0',
                '-vn',  # No video
                '-f', 'wav',
                '-ac', '1',  # Mono
                '-ar', str(self.target_sample_rate),  # Target sample rate
                '-acodec', 'pcm_s16le',  # PCM 16-bit
                '-loglevel', 'error',
                'pipe:1'
            ]
            
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate(input=video_data)
            
            if process.returncode != 0:
                err_msg = stderr.decode().strip() if stderr else "Unknown error"
                raise RuntimeError(f"Audio extraction failed: {err_msg}")
            
            return stdout
            
        except Exception as e:
            raise RuntimeError(f"Failed to extract audio from video: {e}") from e
    
    async def _analyze_audio_basic(self, audio_data: bytes) -> Dict[str, Any]:
        """Basic audio analysis fallback."""
        # Very basic analysis - just estimate duration based on file size
        # This is a rough approximation
        estimated_duration = len(audio_data) / (44100 * 2 * 2)  # Assume 44.1kHz stereo 16-bit
        
        return {
            "duration": max(estimated_duration, 0.1),
            "sample_rate": 44100,  # Default assumption
            "channels": 2,  # Default assumption
            "codec": "unknown",
            "bit_rate": 0,
            "format": "unknown",
            "size": len(audio_data)
        }
    
    def _detect_audio_format(self, audio_data: bytes) -> str:
        """Detect audio format from header."""
        if len(audio_data) < 12:
            return "unknown"
        
        # Check for common audio format headers
        if audio_data[:3] == b'ID3' or audio_data[:2] == b'\xff\xfb':
            return "mp3"
        elif audio_data[:4] == b'RIFF' and audio_data[8:12] == b'WAVE':
            return "wav"
        elif audio_data[:4] == b'fLaC':
            return "flac"
        elif audio_data[:4] == b'OggS':
            return "ogg"
        elif audio_data[4:8] == b'ftyp':
            return "m4a"
        else:
            return "unknown"