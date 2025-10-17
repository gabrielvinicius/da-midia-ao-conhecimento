"""
Media Management Command Handlers - Pure execution logic following Command Pattern
"""
import time
import structlog
from typing import Dict, Any
from uuid import uuid4

from src.media_management.domain.media import Media
from src.media_management.domain.interfaces import (
    IMediaRepository,
    IMediaValidator,
    IMediaUploader,
    IMediaFactory,
    IMediaEventManager,
    IMediaMetricsService
)
from .commands import (
    CreateMediaCommand,
    DeleteMediaCommand,
    ReprocessMediaCommand
)

logger = structlog.get_logger(__name__)


class CreateMediaCommandHandler:
    """Handler for create media command following SOLID principles"""
    
    def __init__(
        self,
        media_repository: IMediaRepository,
        media_validator: IMediaValidator,
        media_uploader: IMediaUploader,
        media_factory: IMediaFactory,
        media_event_manager: IMediaEventManager,
        media_metrics_service: IMediaMetricsService,
    ):
        self.media_repository = media_repository
        self.media_validator = media_validator
        self.media_uploader = media_uploader
        self.media_factory = media_factory
        self.media_event_manager = media_event_manager
        self.media_metrics_service = media_metrics_service

    async def handle(self, command: CreateMediaCommand) -> Dict[str, Any]:
        """Execute media creation command"""
        start_time = time.time()
        media_id = uuid4()
        logger.info("media.upload.started", media_id=str(media_id))

        try:
            # Validate
            self.media_validator.validate_file_content(command.file, command.filename)
            media_type = self.media_validator.get_media_type(command.filename)

            # Upload
            file_path = await self.media_uploader.upload(
                file=command.file,
                user_id=command.user_id,
                media_id=media_id,
                filename=command.filename,
                storage_provider=command.storage_provider,
            )

            # Create Domain Object
            media = self.media_factory.create(
                media_id=media_id,
                user_id=command.user_id,
                file_path=file_path,
                media_type=media_type,
                storage_provider=command.storage_provider,
                transcription_provider=command.transcription_provider,
                summarization_provider=command.summarization_provider,
            )

            # Persist
            saved_media = await self.media_repository.save(media)

            # Publish Event
            await self.media_event_manager.publish_media_uploaded(saved_media)

            # Record Metrics
            duration = time.time() - start_time
            self.media_metrics_service.record_upload_success(
                media_id=saved_media.id,
                duration=duration,
                provider=command.storage_provider,
            )

            logger.info("media.upload.completed", media_id=str(saved_media.id), duration=duration)
            
            return {
                "success": True,
                "media": {
                    "id": str(saved_media.id),
                    "user_id": saved_media.user_id,
                    "filename": command.filename,
                    "media_type": media_type,
                    "file_path": file_path,
                    "storage_provider": command.storage_provider
                },
                "duration": duration,
                "message": "Media uploaded successfully"
            }

        except Exception as e:
            self.media_metrics_service.record_upload_failure()
            logger.error("media.upload.failed", media_id=str(media_id), error=str(e))
            return {
                "success": False,
                "error": str(e),
                "message": f"Media upload failed: {str(e)}"
            }


class DeleteMediaCommandHandler:
    """Handler for delete media command"""
    
    def __init__(
        self,
        media_repository: IMediaRepository,
        media_uploader: IMediaUploader,
        media_event_manager: IMediaEventManager,
    ):
        self.media_repository = media_repository
        self.media_uploader = media_uploader
        self.media_event_manager = media_event_manager

    async def handle(self, command: DeleteMediaCommand) -> Dict[str, Any]:
        """Execute media deletion command"""
        try:
            media = await self.media_repository.get_by_id(command.media_id)
            if not media:
                return {"success": False, "message": "Media not found"}

            if not command.force and str(media.user_id) != str(command.user_id):
                return {"success": False, "message": "Unauthorized: Cannot delete media owned by another user"}

            await self.media_uploader.delete(media.original_file_path)
            success = await self.media_repository.delete(command.media_id)
            if not success:
                return {"success": False, "message": "Failed to delete media from database"}

            await self.media_event_manager.publish_media_deleted(media)
            logger.info("media.deleted", media_id=str(command.media_id), user_id=str(command.user_id))
            
            return {
                "success": True,
                "media_id": str(command.media_id),
                "message": "Media deleted successfully"
            }

        except Exception as e:
            logger.error("media.delete.failed", media_id=str(command.media_id), error=str(e))
            return {
                "success": False,
                "error": str(e),
                "message": f"Media deletion failed: {str(e)}"
            }


class ReprocessMediaCommandHandler:
    """Handler for reprocess media command"""
    
    def __init__(
        self,
        media_repository: IMediaRepository,
        media_event_manager: IMediaEventManager,
    ):
        self.media_repository = media_repository
        self.media_event_manager = media_event_manager

    async def handle(self, command: ReprocessMediaCommand) -> Dict[str, Any]:
        """Execute media reprocessing command"""
        try:
            media = await self.media_repository.get_by_id(command.media_id)
            if not media:
                return {"success": False, "message": "Media not found"}

            if str(media.user_id) != str(command.user_id):
                return {"success": False, "message": "Unauthorized: Cannot reprocess media owned by another user"}

            updated_media = await self.media_repository.update_status(
                command.media_id, 
                "processing"
            )

            await self.media_event_manager.publish_media_reprocess_requested(
                updated_media, 
                command.processing_options or {}
            )

            logger.info("media.reprocess.triggered", 
                       media_id=str(command.media_id), 
                       user_id=str(command.user_id))
            
            return {
                "success": True,
                "media_id": str(command.media_id),
                "status": "processing",
                "processing_options": command.processing_options,
                "message": "Media reprocessing triggered successfully"
            }

        except Exception as e:
            logger.error("media.reprocess.failed", media_id=str(command.media_id), error=str(e))
            return {
                "success": False,
                "error": str(e),
                "message": f"Media reprocessing failed: {str(e)}"
            }