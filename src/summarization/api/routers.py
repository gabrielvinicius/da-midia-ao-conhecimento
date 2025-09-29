# src/summarization/api/routers.py
from fastapi import APIRouter, Depends, HTTPException, status

# Import dependencies from the local module file
from .dependencies import get_summary_queries
from ..application.queries.summary_queries import SummaryQueries
from .schemas import SummaryResponse

router = APIRouter(prefix="/summaries", tags=["Summaries"])


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
