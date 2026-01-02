# src/media_processing/video_processing/infrastructure/video_audio_extractor.py
import asyncio
import io
import os
import json
import tempfile
import wave
from pathlib import Path
from typing import Any, Dict
import subprocess

import structlog

logger = structlog.get_logger(__name__)

class FFmpegVideoAudioExtractor:
    """Video audio extractor using FFmpeg with MoviePy fallback."""

    def __init__(self):
        self.supported_formats = {
            ".mp4",
            ".avi",
            ".mov",
            ".mkv",
            ".wmv",
            ".flv",
            ".webm",
        }

    async def extract_audio(
        self,
        video_data: bytes,
        filename: str,
        output_format: str = "wav",
    ) -> Dict[str, Any]:
        logger.info(
            "ffmpeg_video_audio_extractor.extracting_audio",
            filename=filename,
            output_format=output_format,
        )
        try:
            # Check if file format is supported
            file_ext = Path(filename).suffix.lower()
            if file_ext not in self.supported_formats:
                raise ValueError(f"Formato de vídeo não suportado: {file_ext}")

            # Extract audio using FFmpeg
            audio_data = await self._extract_with_ffmpeg(
                video_data,
                filename,
                output_format,
            )

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
            logger.error(
                "Audio extraction failed",
                error=str(e),
                filename=filename,
            )
            raise

    async def _extract_with_ffmpeg(
        self,
        video_data: bytes,
        filename: str,
        output_format: str,
    ) -> bytes:
        """Extract audio using FFmpeg."""
        # Create temporary files
        with tempfile.NamedTemporaryFile(
            suffix=Path(filename).suffix, delete=False
        ) as video_temp:
            video_temp.write(video_data)
            video_temp_path = video_temp.name

        with tempfile.NamedTemporaryFile(
            suffix=f".{output_format}", delete=False
        ) as audio_temp:
            audio_temp_path = audio_temp.name

        try:
            codec = 'pcm_s16le' if output_format == 'wav' else 'mp3'
            cmd = [
                'ffmpeg', '-y',
                '-i', video_temp_path,
                '-vn',
                '-acodec', codec,
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
                stderr_txt = stderr.decode()
                logger.error(
                    "ffmpeg_audio.failed",
                    stdout=stdout.decode(),
                    stderr=stderr_txt,
                )
                raise RuntimeError(f"FFmpeg falhou ao extrair áudio: {stderr_txt}")

            with open(audio_temp_path, 'rb') as f:
                audio_data = f.read()

            return audio_data

        finally:
            if os.path.exists(video_temp_path):
                os.unlink(video_temp_path)
            if os.path.exists(audio_temp_path):
                os.unlink(audio_temp_path)

    async def _get_audio_metadata(
        self,
        audio_data: bytes,
        audio_format: str,
    ) -> Dict[str, Any]:
        """Get metadata from extracted audio."""
        metadata = {"size_bytes": len(audio_data), "format": audio_format}

        if audio_format == "wav":
            try:
                with wave.open(io.BytesIO(audio_data), "rb") as wav_file:
                    metadata.update(
                        {
                            "channels": wav_file.getnchannels(),
                            "sample_rate": wav_file.getframerate(),
                            "sample_width": wav_file.getsampwidth(),
                            "duration_seconds": (
                                wav_file.getnframes() / wav_file.getframerate()
                            ),
                        }
                    )
            except Exception as e:
                logger.warning("Failed to extract detailed WAV metadata", error=str(e))
        else:
            metadata.update(self._probe_audio_metadata(audio_data, audio_format))

        return metadata

    def _probe_audio_metadata(self, audio_data: bytes, audio_format: str) -> Dict[str, Any]:
        """Extract basic metadata for non-WAV formats using ffprobe."""
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                suffix=f".{audio_format}", delete=False
            ) as audio_temp:
                audio_temp.write(audio_data)
                tmp_path = audio_temp.name

            cmd = [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-show_entries",
                "stream=sample_rate,channels",
                "-of",
                "json",
                tmp_path,
            ]
            result = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                logger.debug(
                    "ffprobe.metadata.failed",
                    stderr=result.stderr.strip(),
                    stdout=result.stdout.strip(),
                )
                return {}

            payload = json.loads(result.stdout or "{}")
            fmt = payload.get("format", {})
            streams = payload.get("streams", [])
            stream0 = streams[0] if streams else {}
            duration = fmt.get("duration")
            channels = stream0.get("channels")
            sample_rate = stream0.get("sample_rate")
            data: Dict[str, Any] = {}
            if duration is not None:
                try:
                    data["duration_seconds"] = float(duration)
                except ValueError:
                    pass
            if channels is not None:
                data["channels"] = channels
            if sample_rate is not None:
                try:
                    data["sample_rate"] = int(sample_rate)
                except ValueError:
                    pass
            return data
        except Exception as exc:
            logger.debug("ffprobe.metadata.exception", error=str(exc))
            return {}
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
