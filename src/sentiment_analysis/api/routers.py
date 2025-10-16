# src/sentiment_analysis/api/routers.py
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Annotated, Any
from jose import JWTError, jwt

# --- Local Dependency Injection and Security Logic ---

from src.auth.domain.user import User, UserRole
from src.auth.config.settings import AuthSettings
from src.auth.application.queries.auth_queries import AuthQueries
from src.auth.infrastructure.oauth2_scheme import oauth2_scheme
from src.media_management.application.queries.media_queries import MediaQueries
from src.sentiment_analysis.application.queries.sentiment_analysis_queries import SentimentAnalysisQueries
from .schemas import SentimentAnalysisResponse

def get_container(request: Request) -> dict:
    return request.app.state.container

def get_sentiment_analysis_queries(container: Annotated[dict, Depends(get_container)]) -> SentimentAnalysisQueries:
    return container["sentiment_analysis_queries"]

def get_media_queries(container: Annotated[dict, Depends(get_container)]) -> MediaQueries:
    return container["media_queries"]

def get_auth_queries(container: Annotated[dict, Depends(get_container)]) -> AuthQueries:
    return container["auth_queries"]

def get_auth_settings(container: Annotated[dict, Depends(get_container)]) -> AuthSettings:
    return container["auth_settings"]

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    settings: Annotated[AuthSettings, Depends(get_auth_settings)],
    queries: Annotated[AuthQueries, Depends(get_auth_queries)],
) -> User:
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("sub")
        if user_id is None: raise credentials_exception
    except JWTError: raise credentials_exception
    user = await queries.get_by_id(user_id)
    if user is None: raise credentials_exception
    return user

# --- Router Definition ---

router = APIRouter(prefix="/sentiment-analysis", tags=["Sentiment Analysis"])

# --- Endpoints ---

@router.get("/", response_model=SentimentAnalysisResponse, summary="Get sentiment analysis result by Media ID")
async def get_sentiment_analysis_by_media_id(
    media_id: UUID,
    queries: SentimentAnalysisQueries = Depends(get_sentiment_analysis_queries),
    media_queries: MediaQueries = Depends(get_media_queries),
    current_user: User = Depends(get_current_user),
):
    media = await media_queries.get_by_id(str(media_id))
    if not media or (str(media.user_id) != str(current_user.id) and current_user.role != UserRole.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this media's analysis")
    analysis_result = await queries.get_by_media_id(str(media_id))
    if not analysis_result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sentiment analysis result not found for the given media ID.")
    return analysis_result
