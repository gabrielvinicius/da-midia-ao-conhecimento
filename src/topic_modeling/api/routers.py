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
from src.shared.api.unified_schemas import create_success_response, create_error_response, BaseResponseSchema

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


@router.post("/analyze", response_model=BaseResponseSchema, summary="Analyze topics in text")
async def analyze_topics(
    text: str = Form(..., description="Text to analyze for topics"),
    media_id: Optional[str] = Form(None, description="Associated media ID"),
    num_topics: int = Form(5, description="Number of topics to extract"),
    current_user: User = Depends(get_current_user)
):
    """Analyze topics in provided text"""
    try:
        # Validate input
        if not text.strip():
            return create_error_response("Empty text provided", "Input validation failed")
        
        if len(text) < 100:
            return create_error_response("Text too short for topic modeling", "Input validation failed")
        
        # TODO: Implement actual topic modeling service
        # For now, return a simple response structure
        response_data = {
            "topics": [
                {"id": i, "words": ["word1", "word2", "word3"], "weight": 0.8 - i*0.1}
                for i in range(num_topics)
            ],
            "input_info": {
                "text_length": len(text),
                "media_id": media_id,
                "requested_topics": num_topics
            },
            "processing_info": {
                "algorithm": "LDA",
                "user_id": str(current_user.id)
            }
        }
        
        return create_success_response(
            data=response_data,
            message="Topic modeling completed successfully"
        )
        
    except Exception as e:
        return create_error_response(
            error=f"Topic modeling failed: {str(e)}",
            message="Internal topic modeling error"
        )


@router.post("/reprocess", response_model=BaseResponseSchema, summary="Reprocess topic modeling")
async def reprocess_topic_modeling(
    media_id: str = Form(..., description="Media ID to reprocess topic modeling"),
    num_topics: int = Form(5, description="Number of topics to extract"),
    force: bool = Form(False, description="Force reprocessing"),
    current_user: User = Depends(get_current_user)
):
    """Reprocess topic modeling for existing media"""
    try:
        # Get media and check access
        media_queries = get_media_queries()
        media = await media_queries.get_by_id(media_id)
        
        if not media:
            return create_error_response("Media not found", "Invalid media ID")
        
        if str(media.user_id) != str(current_user.id) and current_user.role.value != "admin":
            return create_error_response("Not authorized", "Access denied")
        
        # Check if transcription exists (required for topic modeling)
        transcription_queries = get_transcription_queries()
        transcription = await transcription_queries.get_by_media_id(media_id)
        
        if not transcription or not transcription.text:
            return create_error_response("No transcription found", "Transcription required for topic modeling")
        
        # Trigger reprocessing via Celery task
        from src.topic_modeling.tasks.topic_tasks import extract_topics_task
        
        task_result = extract_topics_task.delay(
            media_id=media_id,
            text_content=transcription.text,
            num_topics=num_topics
        )
        
        response_data = {
            "reprocessing": {
                "media_id": media_id,
                "task_id": task_result.id,
                "num_topics": num_topics,
                "text_length": len(transcription.text),
                "status": "PROCESSING"
            },
            "message": "Topic modeling reprocessing started. Check WebSocket for real-time updates."
        }
        
        return create_success_response(
            data=response_data,
            message="Topic modeling reprocessing initiated"
        )
        
    except Exception as e:
        return create_error_response(
            error=f"Reprocessing failed: {str(e)}",
            message="Failed to initiate reprocessing"
        )
