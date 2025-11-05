# src/media_management/services/simple_media_service.py
"""Serviço simplificado de mídia - sem over-engineering
"""
import mimetypes
import uuid
from pathlib import Path
from typing import Optional

import structlog

from src.media_management.domain.media import Media, MediaType
from src.shared.infrastructure.database import get_db
from src.storage.application.services.storage_service import StorageService

logger = structlog.get_logger(__name__)

# Configurações simples
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
ALLOWED_VIDEO_TYPES = {'video/mp4', 'video/avi', 'video/mov', 'video/mkv'}
ALLOWED_AUDIO_TYPES = {'audio/mp3', 'audio/wav', 'audio/m4a', 'audio/flac'}
ALLOWED_TEXT_TYPES = {'text/plain', 'application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}


class SimpleMediaService:
    """Serviço de mídia simplificado sem pipelines complexos"""

    def __init__(self, storage_service: StorageService):
        self.storage_service = storage_service

    async def upload_media(
        self,
        file_content: bytes,
        filename: str,
        user_id: str,
        storage_provider: str = "local",
        transcription_provider: Optional[str] = None,
        summarization_provider: Optional[str] = None
    ) -> Media:
        """Upload de mídia com validação simples"""
        # Validações básicas
        await self._validate_file(file_content, filename)

        # Detectar tipo de mídia
        media_type = self._detect_media_type(filename)

        # Gerar paths únicos
        media_id = str(uuid.uuid4())
        file_path = self._generate_file_path(media_id, filename)

        try:
            # Salvar arquivo
            stored_path = await self.storage_service.store_file(
                file_content, file_path, storage_provider
            )

            # Criar registro no banco
            media = Media(
                id=uuid.UUID(media_id),
                user_id=uuid.UUID(user_id),
                filename=filename,
                original_file_path=stored_path,
                media_type=media_type,
                file_size=len(file_content),
                storage_provider=storage_provider,
                transcription_provider=transcription_provider,
                summarization_provider=summarization_provider,
                status="uploaded"
            )

            # Salvar no banco
            async for db in get_db():
                db.add(media)
                await db.commit()
                await db.refresh(media)
                break

            logger.info("Media uploaded successfully",
                       media_id=media_id, filename=filename)

            # Processar mídia baseado no tipo
            await self._process_media_by_type(media)

            return media

        except Exception as e:
            logger.error("Failed to upload media",
                        error=str(e), filename=filename)
            raise

    async def _validate_file(self, file_content: bytes, filename: str) -> None:
        """Validações simples e diretas"""
        # Validar tamanho
        if len(file_content) > MAX_FILE_SIZE:
            raise ValueError(f"File too large. Max size: {MAX_FILE_SIZE} bytes")

        # Validar se não está vazio
        if len(file_content) == 0:
            raise ValueError("File is empty")

        # Validar tipo MIME
        mime_type, _ = mimetypes.guess_type(filename)
        if not mime_type:
            raise ValueError("Could not determine file type")

        allowed_types = ALLOWED_VIDEO_TYPES | ALLOWED_AUDIO_TYPES | ALLOWED_TEXT_TYPES
        if mime_type not in allowed_types:
            raise ValueError(f"Unsupported file type: {mime_type}")

    def _detect_media_type(self, filename: str) -> MediaType:
        """Detectar tipo de mídia baseado no arquivo"""
        mime_type, _ = mimetypes.guess_type(filename)

        if mime_type in ALLOWED_VIDEO_TYPES:
            return MediaType.VIDEO
        elif mime_type in ALLOWED_AUDIO_TYPES:
            return MediaType.AUDIO
        elif mime_type in ALLOWED_TEXT_TYPES:
            return MediaType.TEXT
        else:
            raise ValueError(f"Unsupported media type: {mime_type}")

    def _generate_file_path(self, media_id: str, filename: str) -> str:
        """Gerar path único para o arquivo"""
        file_extension = Path(filename).suffix
        return f"media/{media_id}/{media_id}{file_extension}"

    async def _process_media_by_type(self, media: Media) -> None:
        """Processar mídia baseado no tipo - sem event bus complexo"""
        try:
            # Encaminhar para a nova task consolidada de processamento
            from src.media_processing.tasks import process_media_task
            logger.info("Dispatching consolidated media processing", media_id=str(media.id))
            process_media_task.delay(media_id=str(media.id))

        except Exception as e:
            logger.error("Failed to schedule media processing",
                        media_id=str(media.id), error=str(e))
            # Não falhar o upload por causa do processamento

    async def reprocess_media(self, media_id: str) -> None:
        """Reprocessar mídia existente"""
        async for db in get_db():
            media = await db.get(Media, media_id)
            if not media:
                raise ValueError(f"Media not found: {media_id}")

            logger.info("Reprocessing media", media_id=media_id)
            await self._process_media_by_type(media)
            break


# Função de conveniência para dependency injection
def get_simple_media_service(storage_service: StorageService) -> SimpleMediaService:
    """Criar instância do serviço simples"""
    return SimpleMediaService(storage_service)
