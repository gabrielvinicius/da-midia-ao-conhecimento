# src/transcription/application/commands/handlers.py
import structlog
from typing import Dict, Any
from uuid import UUID
import time # Adicionar para calcular duração

from src.transcription.domain.interfaces import (
    ISpeechRecognizer,
    ITranscriptionRepository,
    ITranscriptionTaskScheduler,
    TranscriptionOperationLogger,
    TranscriptionMetrics
)
from src.transcription.domain.transcription import Transcription # Para referenciar a entidade Transcription
from src.transcription.application.commands.commands import ProcessTranscriptionCommand, SetSpeakerAliasesCommand
from src.shared.infrastructure.storage.s3_storage_service import S3StorageService # Para baixar o arquivo de áudio

logger = structlog.get_logger(__name__)


class ProcessTranscriptionCommandHandler:
    """Handler for processing a transcription."""

    def __init__(
        self,
        transcription_repo: ITranscriptionRepository,
        speech_recognizer: ISpeechRecognizer,
        storage_service: S3StorageService, # Injetar serviço de armazenamento
        transcription_logger: TranscriptionOperationLogger,
        transcription_metrics: TranscriptionMetrics
    ):
        self.transcription_repo = transcription_repo
        self.speech_recognizer = speech_recognizer
        self.storage_service = storage_service
        self.transcription_logger = transcription_logger
        self.transcription_metrics = transcription_metrics

    async def handle(self, command: ProcessTranscriptionCommand) -> Dict[str, Any]:
        start_time = time.monotonic()
        operation_name = "process_transcription_command"
        success = False
        error = None
        transcription_id_str = ""
        input_audio_length_seconds = 0.0
        output_text_length_chars = 0

        logger.info(
            f"transcription.{operation_name}.started",
            media_id=command.media_id,
            transcription_provider=command.transcription_provider,
            language=command.language
        )
        try:
            # 1. Get the media file (audio data)
            audio_data = await self.storage_service.download_file(command.file_path)
            # TODO: Obter a duração do áudio para input_audio_length_seconds
            # Por enquanto, placeholder
            input_audio_length_seconds = 60.0 # Placeholder

            # 2. Create a new transcription entity in PROCESSING state
            new_transcription = Transcription(
                media_id=UUID(command.media_id),
                provider=command.transcription_provider
            )
            new_transcription.process()
            await self.transcription_repo.add(new_transcription)
            transcription_id_str = str(new_transcription.id)

            # 3. Transcribe the audio data
            transcription_result = await self.speech_recognizer.transcribe(
                audio_data=audio_data,
                language=command.language,
                options={"provider": command.transcription_provider} # Passar o provider como opção
            )

            # 4. Mark transcription as completed
            new_transcription.mark_as_completed(transcription_result)
            await self.transcription_repo.update(new_transcription)
            success = True
            output_text_length_chars = len(new_transcription.text)

            logger.info(
                f"transcription.{operation_name}.completed",
                media_id=command.media_id,
                transcription_id=transcription_id_str
            )
            return {
                "success": True,
                "media_id": command.media_id,
                "transcription_id": transcription_id_str,
                "status": new_transcription.status.value,
                "text_preview": new_transcription.text[:100],
                "message": "Transcription processed successfully"
            }
        except Exception as e:
            error = e
            logger.error(
                f"transcription.{operation_name}.failed",
                media_id=command.media_id,
                error=str(e)
            )
            # Mark transcription as failed in the repository
            transcription = await self.transcription_repo.get_by_media_id(UUID(command.media_id))
            if transcription:
                transcription.mark_as_failed(str(e))
                await self.transcription_repo.update(transcription)
            raise
        finally:
            duration = time.monotonic() - start_time
            await self.transcription_logger.log_operation(
                operation=operation_name,
                media_id=command.media_id,
                provider=command.transcription_provider,
                success=success,
                duration=duration,
                error=error
            )
            await self.transcription_metrics.record_operation(
                operation=operation_name,
                provider=command.transcription_provider,
                duration=duration,
                success=success,
                input_audio_length_seconds=input_audio_length_seconds,
                output_text_length_chars=output_text_length_chars
            )


class SetSpeakerAliasesCommandHandler:
    """Handler for setting speaker aliases in a transcription."""

    def __init__(
        self,
        transcription_repo: ITranscriptionRepository,
        transcription_logger: TranscriptionOperationLogger,
        transcription_metrics: TranscriptionMetrics
    ):
        self.transcription_repo = transcription_repo
        self.transcription_logger = transcription_logger
        self.transcription_metrics = transcription_metrics

    async def handle(self, command: SetSpeakerAliasesCommand) -> Dict[str, Any]:
        start_time = time.monotonic()
        operation_name = "set_speaker_aliases_command"
        success = False
        error = None
        media_id_str = "" # Para logging e métricas
        provider = "unknown" # Não há provider no comando, usar default

        logger.info(
            f"transcription.{operation_name}.started",
            transcription_id=str(command.transcription_id)
        )
        try:
            transcription = await self.transcription_repo.get_by_id(command.transcription_id)
            if not transcription:
                logger.error(f"transcription.{operation_name}.failed", transcription_id=str(command.transcription_id), error="Transcription not found")
                raise ValueError(f"Transcription with ID {command.transcription_id} not found.")

            media_id_str = str(transcription.media_id)
            provider = transcription.provider # Obter o provider da transcrição

            transcription.set_speaker_aliases(command.aliases)
            await self.transcription_repo.update(transcription)
            success = True

            logger.info(
                f"transcription.{operation_name}.completed",
                transcription_id=str(command.transcription_id),
                media_id=media_id_str
            )
            return {
                "success": True,
                "transcription_id": str(command.transcription_id),
                "media_id": media_id_str,
                "message": "Speaker aliases set successfully"
            }
        except Exception as e:
            error = e
            logger.error(
                f"transcription.{operation_name}.failed",
                transcription_id=str(command.transcription_id),
                error=str(e)
            )
            raise
        finally:
            duration = time.monotonic() - start_time
            await self.transcription_logger.log_operation(
                operation=operation_name,
                media_id=media_id_str,
                provider=provider,
                success=success,
                duration=duration,
                error=error
            )
            await self.transcription_metrics.record_operation(
                operation=operation_name,
                provider=provider,
                duration=duration,
                success=success,
                input_audio_length_seconds=0, # Não aplicável diretamente aqui
                output_text_length_chars=0 # Não aplicável diretamente aqui
            )
