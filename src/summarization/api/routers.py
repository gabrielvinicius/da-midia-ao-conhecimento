# src/summarization/api/routers.py
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
from src.summarization.application.queries.summary_queries import SummaryQueries
from .schemas import SummaryResponse

def get_container(request: Request) -> dict:
    return request.app.state.container

def get_summary_queries(container: Annotated[dict, Depends(get_container)]) -> SummaryQueries:
    return container["summary_queries"]

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

router = APIRouter(prefix="/summaries", tags=["Summaries"])

# --- Endpoints ---

@router.get("/", response_model=SummaryResponse, summary="Get a summary by its Media ID")
async def get_summary_by_media_id(
    media_id: UUID,
    queries: SummaryQueries = Depends(get_summary_queries),
    media_queries: MediaQueries = Depends(get_media_queries),
    current_user: User = Depends(get_current_user),
):
    media = await media_queries.get_by_id(str(media_id))
    if not media or (str(media.user_id) != str(current_user.id) and current_user.role != UserRole.ADMIN):
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
    if not media or (str(media.user_id) != str(current_user.id) and current_user.role != UserRole.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this summary")
    return summary
