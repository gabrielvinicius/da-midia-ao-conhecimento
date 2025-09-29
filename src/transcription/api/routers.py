# src/transcription/api/routers.py
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status

# Import dependencies from the local module file and other specific modules
from src.auth.api.dependencies import get_current_user
from src.auth.domain.user import User
from .dependencies import get_transcription_queries, get_media_queries
from src.media_management.application.queries.media_queries import MediaQueries
from src.transcription.application.queries.transcription_queries import TranscriptionQueries
from .schemas import TranscriptionResponse

router = APIRouter(prefix="/transcriptions", tags=["Transcriptions"])


@router.get(
    "/{transcription_id}", 
    response_model=TranscriptionResponse, 
    summary="Get a transcription by its ID",
    description="Retrieves a specific transcription record, including its status and the full transcribed text if completed.",
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Not authorized to access this transcription"},
        404: {"description": "Transcription not found"},
    }
)
async def get_transcription_by_id(
    transcription_id: str,
    queries: TranscriptionQueries = Depends(get_transcription_queries),
    media_queries: MediaQueries = Depends(get_media_queries),
    current_user: User = Depends(get_current_user),
):
    transcription = await queries.get_by_id(transcription_id)
    if not transcription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcription not found")

    # Authorization check
    media = await media_queries.get_by_id(str(transcription.media_id))
    if not media or (str(media.user_id) != str(current_user.id) and current_user.role.value != "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this transcription")

    return transcription
