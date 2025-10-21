# src/summarization/api/routers.py
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status

# Import dependencies from their correct, decoupled locations
from src.shared.api.dependencies import get_current_user
from src.auth.domain.user import User
from .dependencies import get_summary_queries, get_media_queries

from src.summarization.application.queries.summary_queries import SummaryQueries
from src.media_management.application.queries.media_queries import MediaQueries
from .schemas import SummaryResponse
from src.shared.api.unified_schemas import create_success_response, create_error_response, BaseResponseSchema

router = APIRouter(prefix="/summaries", tags=["Summaries"])


@router.get("/", response_model=SummaryResponse, summary="Get a summary by its Media ID")
async def get_summary_by_media_id(
    media_id: UUID,
    queries: SummaryQueries = Depends(get_summary_queries),
    media_queries: MediaQueries = Depends(get_media_queries),
    current_user: User = Depends(get_current_user),
):
    media = await media_queries.get_by_id(str(media_id))
    if not media or (str(media.user_id) != str(current_user.id) and current_user.role.value != "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this media's summary")
    summary = await queries.get_by_media_id(str(media_id))
    if not summary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Summary not found for the given media ID")
    return summary

@router.get("/{summary_id}", response_model=SummaryResponse, summary="Get a summary by its ID")
async def get_summary_by_id(
    summary_id: str, 
    queries: SummaryQueries = Depends(get_summary_queries),
    media_queries: MediaQueries = Depends(get_media_queries),
    current_user: User = Depends(get_current_user),
):
    summary = await queries.get_by_id(summary_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    media = await media_queries.get_by_id(str(summary.media_id))
    if not media or (str(media.user_id) != str(current_user.id) and current_user.role.value != "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this summary")
    return summary


@router.post("/reprocess", response_model=BaseResponseSchema, summary="Reprocess summarization")
async def reprocess_summarization(
    media_id: str = Form(..., description="Media ID to reprocess summary"),
    provider: Optional[str] = Form(None, description="Provider to use for summarization"),
    max_length: Optional[int] = Form(None, description="Maximum summary length"),
    force: bool = Form(False, description="Force reprocessing even if already completed"),
    current_user: User = Depends(get_current_user)
):
    """
    Reprocess summarization for existing media
    Useful for: changing providers, summary length, or fixing failed summaries
    """
    try:
        # Get media and check access
        media_queries = get_media_queries()
        media = await media_queries.get_by_id(media_id)
        
        if not media:
            return create_error_response("Media not found", "Invalid media ID")
        
        if str(media.user_id) != str(current_user.id) and current_user.role.value != "admin":
            return create_error_response("Not authorized", "Access denied")
        
        # Check if transcription exists (required for summarization)
        transcription_queries = get_transcription_queries()
        transcription = await transcription_queries.get_by_media_id(media_id)
        
        if not transcription or not transcription.text:
            return create_error_response("No transcription found", "Transcription required for summarization")
        
        # Trigger reprocessing via Celery task
        from src.summarization.tasks.summary_tasks import process_summary_task
        
        task_result = process_summary_task.delay(
            media_id=media_id,
            text_content=transcription.text,
            provider=provider or media.summarization_provider or "default"
        )
        
        # Update media provider if specified
        if provider:
            media.summarization_provider = provider
        
        response_data = {
            "reprocessing": {
                "media_id": media_id,
                "task_id": task_result.id,
                "provider": provider or media.summarization_provider or "default",
                "max_length": max_length,
                "text_length": len(transcription.text),
                "status": "PROCESSING"
            },
            "message": "Summarization reprocessing started. Check WebSocket for real-time updates."
        }
        
        return create_success_response(
            data=response_data,
            message="Summarization reprocessing initiated"
        )
        
    except Exception as e:
        return create_error_response(
            error=f"Reprocessing failed: {str(e)}",
            message="Failed to initiate reprocessing"
        )
