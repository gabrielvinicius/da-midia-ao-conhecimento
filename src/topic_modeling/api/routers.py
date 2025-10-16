# src/topic_modeling/api/routers.py
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status

# Import dependencies from their correct, decoupled locations
from src.shared.api.dependencies import get_current_user
from src.auth.domain.user import User
from .dependencies import get_topic_modeling_queries, get_media_queries

from src.media_management.application.queries.media_queries import MediaQueries
from ..application.queries.topic_modeling_queries import TopicModelingQueries
from .schemas import TopicModelingResponse

router = APIRouter(prefix="/topic-modeling", tags=["Topic Modeling"])


@router.get("/", response_model=TopicModelingResponse, summary="Get topic modeling result by Media ID")
async def get_topic_modeling_result_by_media_id(
    media_id: UUID,
    queries: TopicModelingQueries = Depends(get_topic_modeling_queries),
    media_queries: MediaQueries = Depends(get_media_queries),
    current_user: User = Depends(get_current_user),
):
    """Retrieves the topic modeling result for a specific media ID."""
    media = await media_queries.get_by_id(str(media_id))
    if not media or (str(media.user_id) != str(current_user.id) and current_user.role.value != "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this media's analysis")

    analysis_result = await queries.get_by_media_id(str(media_id))
    if not analysis_result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic modeling result not found for the given media ID.")

    return analysis_result
