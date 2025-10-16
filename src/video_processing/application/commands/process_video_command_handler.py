# src/video_processing/application/commands/process_video_command_handler.py
import io
import os
import json
import structlog
import av
from pydantic import BaseModel

from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.infrastructure.media_repository import MediaRepository
from src.storage.infrastructure.dependencies import StorageServiceFactory
from src.shared.events.event_bus import EventBus
from src.shared.events.domain_events import AudioExtracted
from src.notifications.infrastructure.connection_manager import ConnectionManager
from .process_video_command import ProcessVideoCommand

logger = structlog.get_logger(__name__)


class ProcessVideoCommandHandler:
    def __init__(
        self,
        media_queries: MediaQueries,
        media_repository: MediaRepository,
        storage_service_factory: StorageServiceFactory,
        event_bus: EventBus,
        connection_manager: ConnectionManager,
    ):
        self.media_queries = media_queries
        self.media_repository = media_repository
        self.storage_service_factory = storage_service_factory
        self.event_bus = event_bus
        self.connection_manager = connection_manager

    async def _push_update(self, entity_name: str, entity: BaseModel, user_id: str):
        """Helper method to push entity updates via WebSocket."""
        message = {
            "type": "entity_update",
            "entity": entity_name,
            "payload": json.loads(entity.model_dump_json())
        }
        await self.connection_manager.send_personal_message(json.dumps(message), user_id)
        logger.info(f"{entity_name}.pushed_realtime_update", id=str(entity.id), user_id=user_id)

    async def handle(self, command: ProcessVideoCommand):
        """Extracts audio from a video file and publishes an event upon completion."""
        logger.info("video.processing.started", media_id=command.media_id)

        media = await self.media_queries.get_by_id(command.media_id)
        if not media:
            raise ValueError(f"Media with id {command.media_id} not found.")

        user_id = str(media.user_id)

        try:
            # 1. Set status to PROCESSING and notify frontend
            media.process()
            await self.media_repository.save(media)
            await self._push_update("media", media, user_id)

            storage_service = self.storage_service_factory.create_storage_service(media.storage_provider)
            video_bytes, _ = await storage_service.download(command.file_path)

            # 2. Extract audio using PyAV
            input_container = av.open(io.BytesIO(video_bytes))
            audio_stream = input_container.streams.audio[0]

            output_buffer = io.BytesIO()
            output_container = av.open(output_buffer, mode="w", format="mp3")
            output_stream = output_container.add_stream("mp3")

            for frame in input_container.decode(audio_stream):
                for packet in output_stream.encode(frame):
                    output_container.mux(packet)
            
            for packet in output_stream.encode():
                output_container.mux(packet)

            output_container.close()
            audio_bytes = output_buffer.getvalue()

            # 3. Save extracted audio and publish event for the next pipeline step
            original_filename, _ = os.path.splitext(os.path.basename(command.file_path))
            audio_file_path = f"processed_audio/{user_id}/{media.id}/{original_filename}.mp3"
            
            await storage_service.upload(audio_file_path, audio_bytes)

            event = AudioExtracted(
                media_id=command.media_id,
                audio_file_path=audio_file_path,
                storage_provider=media.storage_provider,
            )
            await self.event_bus.publish(event)

            logger.info("video.processing.completed", media_id=command.media_id, audio_path=audio_file_path)

        except Exception as e:
            logger.error("video.processing.failed", media_id=command.media_id, error=str(e))
            # 4. In case of failure, update status and notify frontend
            if media:
                media.fail(str(e)[:500])
                await self.media_repository.save(media)
                await self._push_update("media", media, user_id)
            raise
