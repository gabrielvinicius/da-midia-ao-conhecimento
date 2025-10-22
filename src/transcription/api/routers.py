# src/transcription/api/routers.py
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import Optional, Annotated

from src.shared.api.dependencies import get_current_user
from src.auth.domain.user import User
from src.media_management.application.queries.media_queries import MediaQueries # Manter por enquanto, mas idealmente injetar via container

from .dependencies import get_transcription_service, get_process_transcription_command_handler, get_set_speaker_aliases_command_handler
from .schemas import TranscriptionResponse, SpeakerAliasesUpdateRequest
from src.transcription.application.transcription_service import TranscriptionService
from src.transcription.application.commands.commands import ProcessTranscriptionCommand, SetSpeakerAliasesCommand
from src.transcription.application.commands.handlers import ProcessTranscriptionCommandHandler, SetSpeakerAliasesCommandHandler
from src.transcription.domain.transcription import Transcription # Para o retorno
from src.shared.api.unified_schemas import create_success_response, create_error_response, BaseResponseSchema


router = APIRouter(prefix="/transcriptions", tags=["Transcriptions"])


@router.put("/{transcription_id}/speaker-aliases", response_model=BaseResponseSchema, summary="Set Speaker Aliases for a Transcription")
async def set_speaker_aliases(
    transcription_id: UUID,
    request: SpeakerAliasesUpdateRequest,
    transcription_service: Annotated[TranscriptionService, Depends(get_transcription_service)],
    current_user: User = Depends(get_current_user),
):
    """Endpoint to set or update the speaker aliases for a given transcription."""
    try:
        # TODO: Adicionar verificação de autorização baseada no media.user_id
        # Isso exigiria injetar MediaQueries aqui ou ter um método no TranscriptionService
        # para verificar a autorização.
        
        result = await transcription_service.set_speaker_aliases(transcription_id, request.aliases)
        return create_success_response(data=result, message="Speaker aliases set successfully")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/", response_model=TranscriptionResponse, summary="Get a transcription by its Media ID")
async def get_transcription_by_media_id(
    media_id: UUID,
    transcription_service: Annotated[TranscriptionService, Depends(get_transcription_service)],
    current_user: User = Depends(get_current_user),
):
    transcription = await transcription_service.get_transcription_by_media_id(media_id)
    if not transcription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcription not found for the given media ID")
    
    # TODO: Adicionar verificação de autorização baseada no media.user_id
    # Isso exigiria injetar MediaQueries aqui ou ter um método no TranscriptionService
    # para verificar a autorização.
    
    return transcription

@router.get("/{transcription_id}", response_model=TranscriptionResponse, summary="Get a transcription by its ID")
async def get_transcription_by_id(
    transcription_id: UUID, # Mudar para UUID
    transcription_service: Annotated[TranscriptionService, Depends(get_transcription_service)],
    current_user: User = Depends(get_current_user),
):
    transcription = await transcription_service.get_transcription_by_id(transcription_id)
    if not transcription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcription not found")
    
    # TODO: Adicionar verificação de autorização baseada no media.user_id
    # Isso exigiria injetar MediaQueries aqui ou ter um método no TranscriptionService
    # para verificar a autorização.
    
    return transcription


@router.post("/reprocess", response_model=BaseResponseSchema, summary="Reprocess transcription")
async def reprocess_transcription(
    media_id: UUID = Form(..., description="Media ID to reprocess"),
    provider: Optional[str] = Form(None, description="Provider to use (fastwhisper, whisper, etc.)"),
    language: str = Form("auto", description="Language code"),
    force: bool = Form(False, description="Force reprocessing even if already completed"),
    current_user: User = Depends(get_current_user),
    process_transcription_handler: Annotated[ProcessTranscriptionCommandHandler, Depends(get_process_transcription_command_handler)],
    media_queries: MediaQueries = Depends(get_media_queries), # Manter por enquanto
):
    """
    Reprocess transcription for existing media
    Useful for: changing providers, languages, or fixing failed transcriptions
    """
    try:
        # Get media and check access
        media = await media_queries.get_by_id(str(media_id))
        
        if not media:
            return create_error_response("Media not found", "Invalid media ID")
        
        if str(media.user_id) != str(current_user.id) and current_user.role.value != "admin":
            return create_error_response("Not authorized", "Access denied")
        
        # Check if reprocessing is allowed
        if media.status == "PROCESSING" and not force:
            return create_error_response("Media is currently being processed", "Cannot reprocess")
        
        # Criar e executar o comando ProcessTranscriptionCommand
        command = ProcessTranscriptionCommand(
            media_id=str(media_id),
            file_path=media.original_file_path,
            storage_provider=media.storage_provider,
            transcription_provider=provider or media.transcription_provider or "fastwhisper",
            language=language
        )
        
        result = await process_transcription_handler.handle(command)
        
        # TODO: Atualizar media.status, media.transcription_provider, media.language
        # Isso exigiria um media_repository aqui ou um serviço que o handler utiliza.
        # Por enquanto, vou manter aqui para não quebrar a funcionalidade, mas é um ponto de refatoração.

        response_data = {
            "reprocessing": {
                "media_id": str(media_id),
                "task_id": result.get("task_id"), # O handler retorna o resultado, não o task_id diretamente
                "provider": provider or media.transcription_provider or "fastwhisper",
                "language": language,
                "status": "SCHEDULED" # Status da tarefa agendada
            },
            "message": "Transcription reprocessing started. Check WebSocket for real-time updates."
        }
        
        return create_success_response(
            data=response_data,
            message="Transcription reprocessing initiated"
        )
        
    except Exception as e:
        return create_error_response(
            error=f"Reprocessing failed: {str(e)}",
            message="Failed to initiate reprocessing"
        )