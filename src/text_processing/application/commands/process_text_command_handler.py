# src/text_processing/application/commands/process_text_command_handler.py
"""
Process text command handler following SOLID principles.
"""
import structlog
import magic

from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.infrastructure.media_repository import MediaRepository
from src.storage.infrastructure.dependencies import StorageServiceFactory
from src.shared.events.event_bus import EventBus
from src.shared.events.domain_events import TextContentReady
from src.text_processing.application.commands.process_text_command import ProcessTextCommand
from src.text_processing.domain.interfaces import TextProcessingOrchestrator, TextFormat

logger = structlog.get_logger(__name__)


class ProcessTextCommandHandler:
    """
    Command handler for processing text following SOLID principles.
    SRP: Only handles command processing and delegation.
    DIP: Depends on abstractions, not concretions.
    """
    
    def __init__(
        self,
        orchestrator: TextProcessingOrchestrator,
        media_queries: MediaQueries,
        media_repository: MediaRepository,
        storage_service_factory: StorageServiceFactory,
        event_bus: EventBus,
    ):
        self._orchestrator = orchestrator
        self._media_queries = media_queries
        self._media_repository = media_repository
        self._storage_service_factory = storage_service_factory
        self._event_bus = event_bus

    async def handle(self, command: ProcessTextCommand):
        """Handle text processing command."""
        logger.info(
            "text_processing.command.process_started",
            media_id=command.media_id,
            file_path=command.file_path
        )

        media = await self._media_queries.get_by_id(command.media_id)
        if not media:
            raise ValueError(f"Media with id {command.media_id} not found.")

        try:
            # Update media status to processing
            media.process()
            await self._media_repository.save(media)

            # Download file content
            storage_service = self._storage_service_factory.create_storage_service(
                command.storage_provider
            )
            file_bytes, filename = await storage_service.download(command.file_path)

            if not file_bytes:
                raise ValueError("File content is empty or could not be downloaded.")

            # Detect file format
            format_type = await self._detect_file_format(file_bytes, filename)
            
            # Get user ID for notifications
            user_id = str(media.user_id)

            # Delegate to orchestrator (follows DIP)
            text_content = await self._orchestrator.process_text_file(
                media_id=command.media_id,
                file_content=file_bytes,
                format_type=format_type,
                user_id=user_id
            )

            if not text_content.strip():
                raise ValueError("No text content extracted from the file.")

            # Publish event for next pipeline stage
            event = TextContentReady(
                media_id=command.media_id,
                text_content=text_content,
            )
            await self._event_bus.publish(event)

            # Mark media as completed
            media.complete()
            await self._media_repository.save(media)

            logger.info(
                "text_processing.command.process_completed",
                media_id=command.media_id,
                text_length=len(text_content)
            )

        except Exception as e:
            logger.error(
                "text_processing.command.process_failed",
                media_id=command.media_id,
                error=str(e)
            )
            
            # Mark media as failed
            if media:
                media.fail(str(e)[:500])
                await self._media_repository.save(media)
            
            raise
    
    async def _detect_file_format(self, file_content: bytes, filename: str) -> TextFormat:
        """Detect file format from content and filename."""
        try:
            # Use python-magic to detect MIME type
            mime_type = magic.from_buffer(file_content, mime=True)
            
            # Map MIME types to TextFormat
            mime_to_format = {
                "application/pdf": TextFormat.PDF,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": TextFormat.DOCX,
                "text/plain": TextFormat.TXT,
                "text/markdown": TextFormat.MARKDOWN,
                "text/x-markdown": TextFormat.MARKDOWN
            }
            
            detected_format = mime_to_format.get(mime_type)
            
            if detected_format:
                return detected_format
            
            # Fallback: detect by file extension
            if filename:
                extension = filename.lower().split('.')[-1] if '.' in filename else ''
                extension_to_format = {
                    "pdf": TextFormat.PDF,
                    "docx": TextFormat.DOCX,
                    "txt": TextFormat.TXT,
                    "md": TextFormat.MARKDOWN,
                    "markdown": TextFormat.MARKDOWN
                }
                
                format_from_ext = extension_to_format.get(extension)
                if format_from_ext:
                    return format_from_ext
            
            # Default to PDF for backward compatibility
            logger.warning(
                "text_processing.format_detection_failed",
                mime_type=mime_type,
                filename=filename
            )
            return TextFormat.PDF
            
        except Exception as e:
            logger.error(
                "text_processing.format_detection_error",
                filename=filename,
                error=str(e)
            )
            # Default to PDF
            return TextFormat.PDF
