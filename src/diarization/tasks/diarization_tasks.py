# src/diarization/tasks/diarization_tasks.py
import asyncio
import structlog
from celery import shared_task

from src.diarization.infrastructure.dependencies import get_diarization_service
from src.storage.infrastructure.dependencies import get_storage_service_factory
from src.shared.events.event_bus import get_event_bus
from src.shared.events.domain_events import DiarizationCompleted

logger = structlog.get_logger(__name__)

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def diarize_audio_task(self, media_id: str, audio_file_path: str, storage_provider: str):
    """Celery task to perform speaker diarization on an audio file."""
    try:
        return asyncio.run(_run_diarization(media_id, audio_file_path, storage_provider))
    except Exception as e:
        logger.error("diarization.task.failed", media_id=media_id, error=str(e), exc_info=True)
        return None

async def _run_diarization(media_id: str, audio_file_path: str, storage_provider: str):
    """Helper to run diarization logic and publish the result."""
    logger.info("diarization.run.started", media_id=media_id)

    # --- Manual Dependency Injection for Celery Task ---
    diarization_service = get_diarization_service()
    storage_service_factory = get_storage_service_factory()
    storage_service = storage_service_factory(storage_provider)
    event_bus = get_event_bus()

    # Download the audio file to a temporary local path for processing
    audio_bytes, _ = await storage_service.download(audio_file_path)
    
    import tempfile
    import os
    temp_dir = tempfile.gettempdir()
    temp_audio_path = os.path.join(temp_dir, f"{media_id}.wav")

    try:
        with open(temp_audio_path, "wb") as f:
            f.write(audio_bytes)

        # Perform diarization
        diarization_result = diarization_service.diarize(temp_audio_path)

        # Publish the result for the next step in the pipeline
        await event_bus.publish(
            DiarizationCompleted(
                media_id=media_id,
                diarization_result=diarization_result
            )
        )

        logger.info("diarization.run.completed", media_id=media_id, segments_found=len(diarization_result))
        return diarization_result

    finally:
        # Clean up the temporary file
        if os.path.exists(temp_audio_path):
            os.unlink(temp_audio_path)
