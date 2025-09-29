# src/summarization/api/routers.py
from fastapi import APIRouter, Depends, HTTPException, status

from src.auth.api.dependencies import get_current_user
from src.auth.domain.user import User
from .dependencies import get_summarization_service, get_summary_queries
from ..application.summarization_service import SummarizationService
from ..application.queries.summary_queries import SummaryQueries
from .schemas import SummaryResponse, SummaryRequest

router = APIRouter(prefix="/summaries", tags=["Summaries"])


@router.post("/", status_code=status.HTTP_202_ACCEPTED, summary="Request a new summary for a media item")
async def request_summary(
    summary_request: SummaryRequest,
    service: SummarizationService = Depends(get_summarization_service),
    _: User = Depends(get_current_user),
):
    """Requests an asynchronous summarization for a given media item."""
    # The service now correctly expects a media_id
    await service.request_summary(
        media_id=str(summary_request.media_id),
        provider=summary_request.provider,
    )
    return {"message": "Summarization request accepted"}


@router.get("/{summary_id}", response_model=SummaryResponse, summary="Get a summary by its ID")
async def get_summary_by_id(
    summary_id: str, 
    queries: SummaryQueries = Depends(get_summary_queries),
):
    """Retrieves a summary by its ID."""
    summary = await queries.get_by_id(summary_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    return summary
