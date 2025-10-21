# src/text_processing/application/event_handlers.py
import logging
from typing import Dict, Any, Optional # Adicionar Optional

from src.shared.events.event_bus import EventBus
from src.media_management.domain.media import MediaType
from src.shared.events.domain_events import MediaUploaded
from src.text_processing.domain.interfaces import ITextProcessingTaskScheduler # Adicionar esta linha

logger = logging.getLogger(__name__)


async def register_event_handlers(event_bus: EventBus, task_scheduler: ITextProcessingTaskScheduler) -> None: # Adicionar task_scheduler
    """Registers all text processing-related event handlers."""

    async def handle_media_uploaded(event_data: Dict[str, Any]) -> None:
        """Handles MediaUploaded events by triggering the text processing task if the media is a text file."""
        try:
            if event_data.get("media_type") == MediaType.TEXT.value:
                media_id = event_data["media_id"]
                # file_path e storage_provider não são mais passados diretamente para a tarefa
                # A tarefa agora espera text_content, processing_type e options
                # Precisamos obter text_content e processing_type de algum lugar,
                # ou assumir que o evento MediaUploaded já contém essas informações.
                # Por enquanto, vou usar placeholders e assumir que o evento MediaUploaded
                # precisa ser enriquecido ou que a lógica para obter text_content
                # e processing_type virá de outro lugar.

                # Para fins de demonstração e para fazer o código compilar,
                # vou assumir que o evento MediaUploaded pode ter 'text_content' e 'processing_type'
                # ou que eles podem ser inferidos/obtidos aqui.
                # Idealmente, o evento MediaUploaded deveria conter todas as informações necessárias
                # para agendar a tarefa de processamento de texto.

                text_content = event_data.get("text_content", "Default text content from event") # Placeholder
                processing_type = event_data.get("processing_type", "default_processing") # Placeholder
                options = event_data.get("options", {}) # Placeholder

                logger.info(f"Text media uploaded. Dispatching text processing task for media {media_id}")
                await task_scheduler.schedule_process_text_task( # Chamar o scheduler injetado
                    media_id=media_id,
                    text_content=text_content,
                    processing_type=processing_type,
                    options=options
                )

        except KeyError as e:
            logger.error(f"Missing required field in MediaUploaded event data: {e}")
        except Exception as e:
            logger.error(f"Failed to handle MediaUploaded event for text processing: {e}", exc_info=True)

    try:
        event_bus.subscribe(MediaUploaded, handle_media_uploaded)
        logger.info("Successfully registered MediaUploaded handler for text processing.")
    except Exception as e:
        logger.error(f"Failed to register text processing event handlers: {e}", exc_info=True)
        raise