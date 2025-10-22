# src/media_management/application/commands/handlers.py
import structlog
from typing import Dict, Any
from uuid import UUID
import time # Adicionar para calcular duração

from src.media_management.domain.interfaces import IMediaRepository, MediaOperationLogger, MediaMetrics
from src.media_management.domain.media import Media
from src.media_management.domain.enums import MediaStatus
from src.media_management.application.commands.commands import CreateMediaCommand, DeleteMediaCommand, ReprocessMediaCommand

logger = structlog.get_logger(__name__)


class CreateMediaCommandHandler:
    """Handler for creating a new media entry."""

    def __init__(
        self,
        media_repo: IMediaRepository,
        media_logger: MediaOperationLogger,
        media_metrics: MediaMetrics
    ):
        self.media_repo = media_repo
        self.media_logger = media_logger
        self.media_metrics = media_metrics

    async def handle(self, command: CreateMediaCommand) -> Media:
        start_time = time.monotonic()
        operation_name = "create_media_command"
        success = False
        error = None
        file_size_bytes = 0 # Placeholder

        logger.info(
            f"media_management.{operation_name}.started",
            user_id=str(command.user_id),
            media_type=command.media_type.value
        )
        try:
            new_media = Media(
                user_id=command.user_id,
                original_file_path=command.original_file_path,
                media_type=command.media_type,
                storage_provider=command.storage_provider,
                status=MediaStatus.UPLOADED # Estado inicial
            )
            await self.media_repo.add(new_media)
            success = True
            # TODO: Obter o tamanho real do arquivo para file_size_bytes
            file_size_bytes = 1024 * 1024 # Placeholder
            logger.info(
                f"media_management.{operation_name}.completed",
                media_id=str(new_media.id),
                user_id=str(command.user_id)
            )
            return new_media
        except Exception as e:
            error = e
            logger.error(
                f"media_management.{operation_name}.failed",
                user_id=str(command.user_id),
                error=str(e)
            )
            raise
        finally:
            duration = time.monotonic() - start_time
            await self.media_logger.log_operation(
                operation=operation_name,
                media_id="N/A", # Media ID pode não estar disponível em caso de falha na criação
                user_id=str(command.user_id),
                success=success,
                duration=duration,
                error=error
            )
            await self.media_metrics.record_operation(
                operation=operation_name,
                user_id=str(command.user_id),
                media_type=command.media_type.value,
                success=success,
                duration=duration,
                file_size_bytes=file_size_bytes
            )


class DeleteMediaCommandHandler:
    """Handler for deleting a media entry."""

    def __init__(
        self,
        media_repo: IMediaRepository,
        media_logger: MediaOperationLogger,
        media_metrics: MediaMetrics
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
        media_repo: IMediaRepository,
        media_logger: MediaOperationLogger,
        media_metrics: MediaMetrics
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