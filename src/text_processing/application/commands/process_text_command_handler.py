# src/text_processing/application/commands/process_text_command_handler.py
import io
import structlog
import fitz  # PyMuPDF

from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.infrastructure.media_repository import MediaRepository
from src.storage.infrastructure.dependencies import StorageServiceFactory
from src.shared.events.event_bus import EventBus
from src.shared.events.domain_events import TextContentReady
from .process_text_command import ProcessTextCommand

logger = structlog.get_logger(__name__)


class ProcessTextCommandHandler:
    def __init__(
        self,
        media_queries: MediaQueries,
        media_repository: MediaRepository,
        storage_service_factory: StorageServiceFactory,
        event_bus: EventBus,
    ):
        self.media_queries = media_queries
        self.media_repository = media_repository
        self.storage_service_factory = storage_service_factory
        self.event_bus = event_bus

    async def handle(self, command: ProcessTextCommand):
        """Extracts text from a file (e.g., PDF) and publishes an event."""
        logger.info("text.processing.started", media_id=command.media_id)

        media = await self.media_queries.get_by_id(command.media_id)
        if not media:
            raise ValueError(f"Media with id {command.media_id} not found.")

        try:
            media.process()
            await self.media_repository.save(media)

            storage_service = self.storage_service_factory(command.storage_provider)
            file_bytes, _ = await storage_service.download(command.file_path)

            # Extract text from PDF
            doc = fitz.open(stream=io.BytesIO(file_bytes), filetype="pdf")
            text_content = " ".join(page.get_text() for page in doc)
            doc.close()

            if not text_content.strip():
                raise ValueError("No text content found in the file.")

            # Publish the generic event for the next pipeline stage (e.g., summarization)
            event = TextContentReady(
                media_id=command.media_id,
                text_content=text_content,
            )
            await self.event_bus.publish(event)

            media.complete()
            await self.media_repository.save(media)

            logger.info("text.processing.completed", media_id=command.media_id)

        except Exception as e:
            logger.error("text.processing.failed", media_id=command.media_id, error=str(e))
            if media:
                media.fail(str(e)[:500])
                await self.media_repository.save(media)
            raise
