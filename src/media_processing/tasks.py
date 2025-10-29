from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List, Optional
from uuid import UUID
import time

import structlog
from celery import shared_task

from src.shared.infrastructure.database import get_db
from src.transcription.bootstrap import TranscriptionContainer # Will be refactored
from src.transcription.domain.transcription import Transcription # Will be refactored
from src.transcription.infrastructure.transcription_repository import TranscriptionRepository # Will be refactored

# Imports for video processing task
from src.video_processing.infrastructure.video_audio_extractor import FFmpegVideoAudioExtractor # Will be refactored
from src.video_processing.infrastructure.video_thumbnail_generator import FFmpegVideoThumbnailGenerator # Will be refactored
from src.shared.infrastructure.storage.s3_storage_service import S3StorageService # Will be refactored


logger = structlog.get_logger(__name__)

@shared_task
def placeholder_media_processing_task():
    """Placeholder task for media processing."""
    pass

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def process_transcription_task(
        self,
        media_id: str,
        file_path: str,
        storage_provider: str,
        transcription_provider: str,
        language: str = "en",
) -> Optional[str]:
    try:
        return asyncio.run(
            _run_transcription(media_id, file_path, storage_provider, transcription_provider, language)
        )
    except Exception as e:
        logger.error(
            "transcription.task_failed",
            media_id=media_id,
            error=str(e),
            exc_info=True,
        )
        return None


async def _run_transcription(
    media_id: str,
    file_path: str,
    storage_provider: str,
    transcription_provider: str,
    language: str,
) -> Optional[str]:
    media_uuid = UUID(media_id)
    async for db in get_db():
        container = TranscriptionContainer(db=db)

        repo: TranscriptionRepository = container.transcription_repository()
        storage = container.storage_service()
        recognizer = container.speech_recognizer()
        logger.info(
            "transcription.task.start",
            media_id=media_id,
            provider=transcription_provider,
            language=language,
        )

        transcription = await repo.get_by_media_id(media_uuid)
        if transcription is None:
            transcription = Transcription(
                media_id=media_uuid,
                provider=transcription_provider,
            )
            transcription.process()
            await repo.add(transcription)

        try:
            audio_bytes = await storage.download_file(file_path)
            result_payload = await recognizer.transcribe(audio_bytes, language=language)

            transcription.mark_as_completed(result_payload)
            await repo.update(transcription)
            await db.commit()

            logger.info(
                "transcription.task.completed",
                media_id=media_id,
                transcription_id=str(transcription.id),
            )
            return str(transcription.id)
        except Exception as exc:
            logger.error(
                "transcription.task.error",
                media_id=media_id,
                error=str(exc),
                exc_info=True,
            )
            transcription.mark_as_failed(str(exc))
            await repo.update(transcription)
            await db.commit()
            raise

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def process_video_task(
        self,
        media_id: str,
        file_path: str,
        storage_provider: str,
) -> Optional[Dict[str, Any]]:
    try:
        return asyncio.run(
            _run_video_processing(media_id, file_path, storage_provider)
        )
    except Exception as e:
        logger.error(
            "video_processing.task_failed",
            media_id=media_id,
            error=str(e),
            exc_info=True,
        )
        return None

async def _run_video_processing(
    media_id: str,
    file_path: str,
    storage_provider: str,
) -> Optional[Dict[str, Any]]:
    start_time = time.monotonic()
    success = False
    error = None

    # TODO: Resolve dependencies via DI container later
    audio_extractor = FFmpegVideoAudioExtractor()
    thumbnail_generator = FFmpegVideoThumbnailGenerator()
    storage = S3StorageService() # Assuming S3 for now, will be dynamic later

    logger.info("video_processing.process.started", media_id=media_id, file_path=file_path)
    try:
        # 1. Download the video file
        video_data = await storage.download_file(file_path)
        
        # 2. Extract audio
        audio_result = await audio_extractor.extract_audio(
            video_data=video_data,
            filename=file_path,
            output_format='wav'
        )
        
        # 3. Generate thumbnail
        thumbnail_result = await thumbnail_generator.generate_thumbnail(
            video_data=video_data,
            filename=file_path,
            size='medium',
            timestamp=5.0
        )
        
        success = True
        logger.info("video_processing.process.completed", media_id=media_id)
        return {
            "success": True,
            "media_id": media_id,
            "audio_extraction_result": audio_result,
            "thumbnail_generation_result": thumbnail_result,
            "message": "Video processed successfully"
        }
    except Exception as e:
        error = e
        logger.error("video_processing.process.failed", media_id=media_id, error=str(e))
        raise
    finally:
        duration = time.monotonic() - start_time
        # TODO: Adicionar logging e métricas aqui
        # await self.logger.log_operation(...) # Placeholder
        # await self.metrics.record_operation(...) # Placeholder