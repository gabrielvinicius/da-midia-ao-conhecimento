from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.media_management.api.dependencies import get_media_service
from src.media_management.application.dtos import GetMediaQuery
from src.media_management.application.services.media_service import MediaService
from src.media_processing.application.dtos import (
    GetTranscriptionByIdQuery,
    GetTranscriptionByMediaIdQuery,
    SetSpeakerAliasesCommand,
)
from src.media_processing.application.services.transcription_service import (
    TranscriptionService,
)
from src.shared.application.schemas import (
    BaseResponseSchema,
    create_success_response,
)
from src.user_management.api.dependencies import get_current_user
from src.user_management.domain import User, UserRole

from .dependencies import (
    get_transcription_service,
)
from .schemas import SpeakerAliasesUpdateRequest, TranscriptionResponse

router = APIRouter(prefix="/transcriptions", tags=["Transcriptions"])


async def _ensure_media_access(
    media_id: UUID, media_service: MediaService, current_user: User
) -> None:
    """Garante que a mídia existe e pertence ao usuário (ou que ele é admin)."""
    media = await media_service.get_media(GetMediaQuery(media_id=media_id))
    if not media:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mídia não encontrada")
    if str(media.user_id) != str(current_user.id) and current_user.role != UserRole.ADMIN:
        # 404, como nas rotas de mídia: um 403 confirmaria que o ID existe.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mídia não encontrada")


@router.put(
    "/{transcription_id}/speaker-aliases",
    response_model=BaseResponseSchema,
    summary="Set Speaker Aliases for a Transcription",
)
async def set_speaker_aliases(
    transcription_id: UUID,  # Path parameter
    request_data: SpeakerAliasesUpdateRequest,  # Request body
    transcription_service: TranscriptionService = Depends(get_transcription_service),
    media_service: MediaService = Depends(get_media_service),
    current_user: User = Depends(get_current_user),
):
    """Endpoint to set or update the speaker aliases for a given transcription."""
    transcription = await transcription_service.get_transcription_by_id(
        GetTranscriptionByIdQuery(transcription_id=transcription_id)
    )
    if not transcription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcription not found")
    await _ensure_media_access(transcription.media_id, media_service, current_user)
    # Erros saem pelos tratadores globais; um erro inesperado vira 500 sem
    # expor a mensagem interna (antes, ela ia ao cliente).
    result = await transcription_service.set_speaker_aliases(
        SetSpeakerAliasesCommand(transcription_id=transcription_id, aliases=request_data.aliases)
    )
    return create_success_response(data=result, message="Speaker aliases set successfully")


@router.get(
    "/",
    response_model=TranscriptionResponse,
    summary="Get a transcription by its Media ID",
)
async def get_transcription_by_media_id(
    media_id: UUID = Query(
        ...,
        description="Media ID to get transcription for.",
    ),
    transcription_service: TranscriptionService = Depends(get_transcription_service),
    media_service: MediaService = Depends(get_media_service),
    current_user: User = Depends(get_current_user),
):
    await _ensure_media_access(media_id, media_service, current_user)
    query = GetTranscriptionByMediaIdQuery(media_id=media_id)
    transcription = await transcription_service.get_transcription_by_media_id(query)
    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcription not found for the given media ID",
        )

    # Explicit mapping
    return TranscriptionResponse(
        id=transcription.id,
        media_id=transcription.media_id,
        text=transcription.text,
        language=transcription.language,
        status=transcription.status.value,
        confidence_score=transcription.confidence_score,
        created_at=transcription.created_at,
        processed_at=transcription.processed_at,
        speaker_aliases=transcription.speaker_aliases,
        segments=transcription.segments,
        error_message=transcription.error_message
    )


@router.get(
    "/media/{media_id}/estimate",
    summary="Estimate how long a media takes to process",
)
async def estimate_processing(
    media_id: UUID,
    transcription_service: TranscriptionService = Depends(get_transcription_service),
    media_service: MediaService = Depends(get_media_service),
    current_user: User = Depends(get_current_user),
):
    """Tempo estimado (transcrição + análise), a partir da duração da
    gravação e da velocidade medida nos processamentos anteriores.
    estimated_seconds é nulo quando não há base para estimar."""
    await _ensure_media_access(media_id, media_service, current_user)
    return await transcription_service.estimate_processing(media_id)


@router.get(
    "/{transcription_id}",
    response_model=TranscriptionResponse,
    summary="Get a transcription by its ID",
)
async def get_transcription_by_id(
    transcription_id: UUID,
    transcription_service: TranscriptionService = Depends(get_transcription_service),
    media_service: MediaService = Depends(get_media_service),
    current_user: User = Depends(get_current_user),
):
    query = GetTranscriptionByIdQuery(transcription_id=transcription_id)
    transcription = await transcription_service.get_transcription_by_id(query)
    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcription not found",
        )
    await _ensure_media_access(transcription.media_id, media_service, current_user)

    # Explicit mapping
    return TranscriptionResponse(
        id=transcription.id,
        media_id=transcription.media_id,
        text=transcription.text,
        language=transcription.language,
        status=transcription.status.value,
        confidence_score=transcription.confidence_score,
        created_at=transcription.created_at,
        processed_at=transcription.processed_at,
        speaker_aliases=transcription.speaker_aliases,
        segments=transcription.segments,
        error_message=transcription.error_message
    )
