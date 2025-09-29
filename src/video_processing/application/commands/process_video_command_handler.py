# src/video_processing/application/commands/process_video_command_handler.py
import io
import os
import structlog
import av

from src.media_management.application.queries.media_queries import MediaQueries
from src.storage.infrastructure.dependencies import StorageServiceFactory
from src.shared.events.event_bus import EventBus
from src.shared.events.domain_events import AudioExtracted
from .process_video_command import ProcessVideoCommand

logger = structlog.get_logger(__name__)


class ProcessVideoCommandHandler:
    def __init__(
        self,
        media_queries: MediaQueries,
        storage_service_factory: StorageServiceFactory,
        event_bus: EventBus,
    ):
        self.media_queries = media_queries
        self.storage_service_factory = storage_service_factory
        self.event_bus = event_bus

    async def handle(self, command: ProcessVideoCommand):
        """Extracts audio from a video file and publishes an event upon completion."""
        logger.info("video.processing.started", media_id=command.media_id)

        try:
            media = await self.media_queries.get_by_id(command.media_id)
            if not media:
                raise ValueError(f"Media with id {command.media_id} not found.")

            storage_service = self.storage_service_factory(media.storage_provider)
            video_bytes, _ = await storage_service.download(command.file_path)

            # Extract audio using PyAV (ffmpeg bindings)
            input_container = av.open(io.BytesIO(video_bytes))
            audio_stream = input_container.streams.audio[0]

            output_buffer = io.BytesIO()
            output_container = av.open(output_buffer, mode="w", format="mp3")
            output_stream = output_container.add_stream("mp3")

            for frame in input_container.decode(audio_stream):
                for packet in output_stream.encode(frame):
                    output_container.mux(packet)
            
            # Flush the container to write any remaining packets
            for packet in output_stream.encode():
                output_container.mux(packet)

            output_container.close()
            audio_bytes = output_buffer.getvalue()

            # Save the extracted audio back to storage
            original_filename, _ = os.path.splitext(os.path.basename(command.file_path))
            audio_file_path = f"processed_audio/{media.user_id}/{media.id}/{original_filename}.mp3"
            
            await storage_service.upload(audio_file_path, audio_bytes)

            # Publish the event
            event = AudioExtracted(
                media_id=command.media_id,
                audio_file_path=audio_file_path,
                storage_provider=media.storage_provider,
            )
            await self.event_bus.publish(event)

            logger.info("video.processing.completed", media_id=command.media_id, audio_path=audio_file_path)

        except Exception as e:
            logger.error("video.processing.failed", media_id=command.media_id, error=str(e))
            # Here you might want to update the media status to FAILED
            # and publish a VideoProcessingFailed event.
            raise
