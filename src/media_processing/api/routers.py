"""Rotas das transcrições.

Quem pode ver cada transcrição é decidido pelo serviço (o dono da mídia,
gravado na transcrição, ou um administrador; 404 para os demais). Antes, cada
rota consultava o módulo de mídias para isso, com mensagens em inglês.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from src.media_processing.application.dtos import (
    GetTranscriptionByIdQuery,
    GetTranscriptionByMediaIdQuery,
    SetSpeakerAliasesCommand,
)
from src.media_processing.application.services.transcription_service import TranscriptionService
from src.media_processing.domain import Transcription
from src.shared.application.access import Requester
from src.user_management.api.dependencies import get_requester

from .dependencies import get_transcription_service
from .schemas import SpeakerAliasesUpdateRequest, TranscriptionResponse

router = APIRouter(prefix="/transcriptions", tags=["Transcriptions"])


def _response(transcription: Transcription) -> TranscriptionResponse:
    return TranscriptionResponse(
        id=transcription.id,
        media_id=transcription.media_id,
        text=transcription.text,
        language=transcription.language,
        status=transcription.status,
        provider=transcription.provider,
        confidence_score=transcription.confidence_score,
        created_at=transcription.created_at,
        processed_at=transcription.processed_at,
        speaker_aliases=transcription.speaker_aliases,
        segments=transcription.segments,
        error_message=transcription.error_message,
    )


@router.get("/", response_model=TranscriptionResponse, summary="Transcrição de uma mídia")
async def get_transcription_by_media_id(
    media_id: UUID = Query(..., description="Mídia da transcrição."),
    service: TranscriptionService = Depends(get_transcription_service),
    requester: Requester = Depends(get_requester),
):
    return _response(
        await service.get_transcription_by_media_id(GetTranscriptionByMediaIdQuery(media_id=media_id), requester)
    )


@router.get("/media/{media_id}/estimate", summary="Tempo estimado do processamento de uma mídia")
async def estimate_processing(
    media_id: UUID,
    service: TranscriptionService = Depends(get_transcription_service),
    requester: Requester = Depends(get_requester),
):
    """Transcrição + análise, pela duração da gravação e pela velocidade medida
    nos processamentos anteriores; estimated_seconds é nulo sem base para estimar."""
    return await service.estimate_processing(media_id, requester)


@router.get("/{transcription_id}", response_model=TranscriptionResponse, summary="Transcrição pelo id")
async def get_transcription_by_id(
    transcription_id: UUID,
    service: TranscriptionService = Depends(get_transcription_service),
    requester: Requester = Depends(get_requester),
):
    return _response(
        await service.get_transcription_by_id(GetTranscriptionByIdQuery(transcription_id=transcription_id), requester)
    )


@router.put("/{transcription_id}/speaker-aliases", response_model=TranscriptionResponse, summary="Nomes dos falantes")
async def set_speaker_aliases(
    transcription_id: UUID,
    body: SpeakerAliasesUpdateRequest,
    service: TranscriptionService = Depends(get_transcription_service),
    requester: Requester = Depends(get_requester),
):
    return _response(
        await service.set_speaker_aliases(
            SetSpeakerAliasesCommand(transcription_id=transcription_id, aliases=body.aliases), requester
        )
    )
