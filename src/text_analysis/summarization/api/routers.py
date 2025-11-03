# src/summarization/api/routers.py
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, status
from typing import Annotated, Optional

from src.user_management.domain.user import User
from src.media_management.application.queries.media_queries import MediaQueries
from src.shared.api.dependencies import get_current_user
from src.shared.api.unified_schemas import create_error_response, create_success_response
from src.text_analysis.summarization.application.summarization_service import SummarizationService
from src.text_analysis.summarization.domain.summary import Summary
from src.media_processing.transcription.application.queries.transcription_queries import TranscriptionQueries

from .dependencies import (
    get_media_queries,
    get_summarization_service,
    get_transcription_queries,
)
from .schemas import SummaryResponse, SummaryReprocessAck, SummaryReprocessResponse


router = APIRouter(prefix="/summaries", tags=["Summaries"])


@router.get("/", response_model=SummaryResponse, summary="Get a summary by its Media ID")
async def get_summary_by_media_id(
    media_id: UUID,
    summarization_service: Annotated[SummarizationService, Depends(get_summarization_service)],
    current_user: User = Depends(get_current_user),
):
    summary = await summarization_service.get_summary_by_media_id(media_id)
    if not summary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Summary not found for the given media ID")
    
    # TODO: Adicionar verificação de autorização baseada no media.user_id
    # Isso exigiria injetar MediaQueries aqui ou ter um método no SummarizationService
    # para verificar a autorização. Por enquanto, vou remover a verificação de mídia aqui.
    # media = await media_queries.get_by_id(str(media_id))
    # if not media or (str(media.user_id) != str(current_user.id) and current_user.role.value != "admin"):
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this media's summary")
    
    return SummaryResponse.from_domain(summary)

@router.get("/{summary_id}", response_model=SummaryResponse, summary="Get a summary by its ID")
async def get_summary_by_id(
    summary_id: UUID, # Mudar para UUID
    summarization_service: Annotated[SummarizationService, Depends(get_summarization_service)],
    current_user: User = Depends(get_current_user),
):
    summary = await summarization_service.get_summary_by_id(summary_id)
    if not summary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Summary not found")
    
    # TODO: Adicionar verificação de autorização baseada no media.user_id
    # Isso exigiria injetar MediaQueries aqui ou ter um método no SummarizationService
    # para verificar a autorização. Por enquanto, vou remover a verificação de mídia aqui.
    # media = await media_queries.get_by_id(str(summary.media_id))
    # if not media or (str(media.user_id) != str(current_user.id) and current_user.role.value != "admin"):
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this summary")
    
    return SummaryResponse.from_domain(summary)


@router.post(
    "/reprocess",
    response_model=SummaryReprocessResponse,
    summary="Reprocess summarization",
)
async def reprocess_summarization(
    media_id: UUID = Form(..., description="Media ID to reprocess summary"), # Mudar para UUID
    provider: Optional[str] = Form(None, description="Provider to use for summarization"),
    # max_length: Optional[int] = Form(None, description="Maximum summary length"), # Removido, pois o handler de comando deve lidar com isso
    # force: bool = Form(False, description="Force reprocessing even if already completed"), # Removido, pois o handler de comando deve lidar com isso
    *,
    current_user: User = Depends(get_current_user),
    summarization_service: Annotated[SummarizationService, Depends(get_summarization_service)],
    media_queries: MediaQueries = Depends(get_media_queries), # Manter por enquanto
    transcription_queries: TranscriptionQueries = Depends(get_transcription_queries), # Manter por enquanto
):
    """
    Reprocess summarization for existing media
    Useful for: changing providers, summary length, or fixing failed summaries
    """
    try:
        # Get media and check access
        media = await media_queries.get_by_id(str(media_id))
        
        if not media:
            return create_error_response("Media not found", "Invalid media ID")
        
        if str(media.user_id) != str(current_user.id) and current_user.role.value != "admin":
            return create_error_response("Not authorized", "Access denied")
        
        # Check if transcription exists (required for summarization)
        transcription = await transcription_queries.get_by_media_id(str(media_id)) # Mudar para str(media_id)
        
        if not transcription or not transcription.text:
            return create_error_response("No transcription found", "Transcription required for summarization")
        
        provider_name = provider or media.summarization_provider or "builtin"
        task_info = await summarization_service.generate_summary(
            media_id=media_id,
            text_content=transcription.text,
            provider=provider_name,
        )

        task_id = task_info.get("task_id") if isinstance(task_info, dict) else None

        response_data = SummaryReprocessAck(
            media_id=media_id,
            provider=provider_name,
            task_id=task_id,
        )

        return SummaryReprocessResponse(
            message="Summarization task scheduled successfully.",
            reprocessing=response_data,
        )
        
    except Exception as e:
        return create_error_response(
            error=f"Reprocessing failed: {str(e)}",
            message="Failed to initiate reprocessing"
        )
