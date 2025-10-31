# src/media_management/application/commands/handlers.py
import time  # Adicionar para calcular duração

import structlog

from src.media_management.application.commands.commands import DeleteMediaCommand, ReprocessMediaCommand
from src.media_management.infrastructure.logging import StructuredMediaLogger
from src.media_management.infrastructure.media_repository import MediaRepository
from src.media_management.infrastructure.metrics import PrometheusMediaMetrics

logger = structlog.get_logger(__name__)


class DeleteMediaCommandHandler:
    """Handler for deleting a media entry."""

    def __init__(
        self,
        media_repo: MediaRepository,
        media_logger: StructuredMediaLogger,
        media_metrics: PrometheusMediaMetrics
    ):
        self.media_repo = media_repo
        self.media_logger = media_logger
        self.media_metrics = media_metrics

    async def handle(self, command: DeleteMediaCommand) -> None:
        start_time = time.monotonic()
        operation_name = "delete_media_command"
        success = False
        error = None
        user_id_str = "N/A" # Placeholder
        media_type_str = "N/A" # Placeholder
        file_size_bytes = 0 # Placeholder

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
            file_size_bytes = 1024 * 1024 # Placeholder

            await self.media_repo.delete(media)
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
        user_id_str = "N/A" # Placeholder
        media_type_str = "N/A" # Placeholder
        file_size_bytes = 0 # Placeholder

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
            file_size_bytes = 1024 * 1024 # Placeholder

            media.process() # Marcar como processando
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
