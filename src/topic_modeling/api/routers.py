# src/topic_modeling/api/routers.py
from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query

from src.auth.api.dependencies import get_current_user
from src.auth.domain.user import User
from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.api.dependencies import get_media_queries
from .dependencies import get_topic_modeling_queries
from .schemas import TopicModelingResponse
from ..application.queries.topic_modeling_queries import TopicModelingQueries

router = APIRouter(prefix="/topic-modeling", tags=["Topic Modeling"])


@router.get("/", response_model=List[TopicModelingResponse], summary="List topic modeling results or get by Media ID")
async def list_topic_modeling_results(
    media_id: Optional[UUID] = Query(None, description="Filter by media ID"),
    queries: TopicModelingQueries = Depends(get_topic_modeling_queries),
    media_queries: MediaQueries = Depends(get_media_queries),
    current_user: User = Depends(get_current_user),
):
    """List all topic modeling results for current user or get specific by media_id."""
    if media_id:
        # Get specific result by media_id
        media = await media_queries.get_by_id(str(media_id))
        if not media or (str(media.user_id) != str(current_user.id) and current_user.role.value != "admin"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this media's analysis")

        analysis_result = await queries.get_by_media_id(str(media_id))
        if not analysis_result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic modeling result not found for the given media ID.")

        return [analysis_result]
    else:
        # List all results for current user - return empty for now
        return []
