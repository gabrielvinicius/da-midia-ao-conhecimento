# src/media_management/application/commands/handlers.py
import time

import structlog
from uuid import UUID

from src.media_management.application.commands.commands import (
    DeleteMediaCommand,
    ReprocessMediaCommand,
)
from src.media_management.infrastructure.logging import StructuredMediaLogger
from src.media_management.infrastructure.media_repository import MediaRepository
from src.media_management.infrastructure.metrics import PrometheusMediaMetrics
from src.media_processing.transcription.infrastructure.transcription_repository import TranscriptionRepository
from src.storage.infrastructure.dependencies import StorageServiceFactory

logger = structlog.get_logger(__name__)


class DeleteMediaCommandHandler:
    """Handler for deleting a media entry."""

    def __init__(
        self,
        media_repo: MediaRepository,
        media_logger: StructuredMediaLogger,
        media_metrics: PrometheusMediaMetrics,
        storage_factory: StorageServiceFactory,
    ):
        self.media_repo = media_repo
        self.media_logger = media_logger
        self.media_metrics = media_metrics
        self.storage_factory = storage_factory

    async def handle(self, command: DeleteMediaCommand) -> None:
        start_time = time.monotonic()
        operation_name = "delete_media_command"
        success = False
        error = None
        user_id_str = "N/A"
        media_type_str = "N/A"
        file_size_bytes = 0

        logger.info(
            f"media_management.{operation_name}.started",
            media_id=str(command.media_id)
        )
        try:
            media = await self.media_repo.get_by_id(command.media_id)
            if not media:
                raise ValueError(f"Media with ID {command.media_id} not found.")

            user_id_str = str(media.user_id)
            media_type_str = media.media_type.value
            # TODO: Obter o tamanho real do arquivo para file_size_bytes
            file_size_bytes = 1024 * 1024 

            # Delete associated records (TranscriptionRepo handles its own commit)
            await self._delete_associated_records(media.id)
            
            # Delete file from storage (No transaction needed)
            await self._delete_original_file(media)
            
            # Delete media record (MediaRepo handles its own commit now)
            await self.media_repo.delete(media.id)

            # Removed manual session commit here as Repositories now handle it
            
            success = True
            logger.info(
                f"media_management.{operation_name}.completed",
                media_id=str(command.media_id)
            )
        except Exception as e:
            error = e
            logger.error(
                f"media_management.{operation_name}.failed",
                media_id=str(command.media_id),
                error=str(e)
            )
            raise
        finally:
            duration = time.monotonic() - start_time
            await self.media_logger.log_operation(
                operation=operation_name,
                media_id=str(command.media_id),
                user_id=user_id_str,
                success=success,
                duration=duration,
                error=error
            )
            await self.media_metrics.record_operation(
                operation=operation_name,
                user_id=user_id_str,
                media_type=media_type_str,
                success=success,
                duration=duration,
                file_size_bytes=file_size_bytes
            )

    async def _delete_associated_records(self, media_id: UUID) -> None:
        db = getattr(self.media_repo, "db", None)
        if db is None:
            return

        transcription_repo = TranscriptionRepository(db)

        try:
            await transcription_repo.delete_by_media_id(media_id)
        except Exception as exc:
            logger.warning("media.delete.transcription_failed", media_id=str(media_id), error=str(exc))

    async def _delete_original_file(self, media) -> None:
        file_path = getattr(media, "original_file_path", None)
        if not file_path:
            return

        provider = (getattr(media, "storage_provider", None) or "local").lower()
        storage_client = self.storage_factory.create_storage_service(provider)
        try:
            await storage_client.delete(file_path)
        except FileNotFoundError:
            logger.info("media.delete.file_missing", path=file_path, provider=provider)
        except Exception as exc:
            logger.warning("media.delete.file_failed", path=file_path, provider=provider, error=str(exc))


class ReprocessMediaCommandHandler:
    """Handler for reprocessing a media entry."""

    def __init__(
        self,
        media_repo: MediaRepository,
        media_logger: StructuredMediaLogger,
        media_metrics: PrometheusMediaMetrics
    ):
        self.media_repo = media_repo
        self.media_logger = media_logger
        self.media_metrics = media_metrics

    async def handle(self, command: ReprocessMediaCommand) -> None:
        start_time = time.monotonic()
        operation_name = "reprocess_media_command"
        success = False
        error = None
        user_id_str = "N/A"
        media_type_str = "N/A"
        file_size_bytes = 0

        logger.info(
            f"media_management.{operation_name}.started",
            media_id=str(command.media_id)
        )
        try:
            media = await self.media_repo.get_by_id(command.media_id)
            if not media:
                raise ValueError(f"Media with ID {command.media_id} not found.")

            user_id_str = str(media.user_id)
            media_type_str = media.media_type.value
            file_size_bytes = 1024 * 1024 

            media.process() # Marcar como processando
            # MediaRepo handles commit
            await self.media_repo.update(media)
            
            # Disparar reprocessamento via Celery
            try:
                from src.media_processing.tasks import process_media_task
                process_media_task.delay(media_id=str(command.media_id))
            except Exception as dispatch_exc:  # best-effort scheduling
                logger.warning(
                    "media_management.reprocess_media.schedule_failed",
                    media_id=str(command.media_id),
                    error=str(dispatch_exc),
                )
            success = True
            logger.info(
                f"media_management.{operation_name}.completed",
                media_id=str(command.media_id)
            )
        except Exception as e:
            error = e
            logger.error(
                f"media_management.{operation_name}.failed",
                media_id=str(command.media_id),
                error=str(e)
            )
            raise
        finally:
            duration = time.monotonic() - start_time
            await self.media_logger.log_operation(
                operation=operation_name,
                media_id=str(command.media_id),
                user_id=user_id_str,
                success=success,
                duration=duration,
                error=error
            )
            await self.media_metrics.record_operation(
                operation=operation_name,
                user_id=user_id_str,
                media_type=media_type_str,
                success=success,
                duration=duration,
                file_size_bytes=file_size_bytes
            )