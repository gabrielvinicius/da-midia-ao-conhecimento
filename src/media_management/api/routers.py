# src/media_management/api/routers.py
from typing import Optional, List, Annotated, Any
from uuid import UUID
from fastapi import APIRouter, UploadFile, Depends, HTTPException, status, File, Query, Request
from fastapi.encoders import jsonable_encoder
from jose import JWTError, jwt

# --- Local Dependency Injection and Security Logic ---

from src.auth.domain.user import User, UserRole
from src.auth.config.settings import AuthSettings
from src.auth.application.queries.auth_queries import AuthQueries
from src.auth.infrastructure.oauth2_scheme import oauth2_scheme
from .dependencies import get_media_service, get_media_queries, get_media_settings
from ..application.media_service import MediaService
from ..application.queries.media_queries import MediaQueries
from .schemas import MediaResponse

def get_container(request: Request) -> dict:
    return request.app.state.container

def get_media_service(container: Annotated[dict, Depends(get_container)]) -> MediaService:
    return container["media_service"]

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

router = APIRouter(prefix="/media", tags=["Media"])

# --- Endpoints ---

@router.post("/", response_model=MediaResponse, status_code=status.HTTP_201_CREATED)
async def create_media(
    file: UploadFile = File(...),
    storage_provider: Optional[str] = Query("local"),
    transcription_provider: Optional[str] = Query(None),
    summarization_provider: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    media_service: MediaService = Depends(get_media_service),
):
    try:
        command = CreateMediaCommand(
            user_id=str(current_user.id),
            file=await file.read(),
            filename=file.filename,
            storage_provider=storage_provider,
            transcription_provider=transcription_provider,
            summarization_provider=summarization_provider
        )
        media = await media_service.create_media(command)
        return jsonable_encoder(media)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/", response_model=List[MediaResponse])
async def list_user_media(
    current_user: User = Depends(get_current_user),
    media_queries: MediaQueries = Depends(get_media_queries),
):
    media_list = await media_queries.list_by_user(user_id=str(current_user.id))
    return jsonable_encoder(media_list)

@router.get("/{media_id}", response_model=MediaResponse)
async def get_media_by_id(
    media_id: UUID,
    current_user: User = Depends(get_current_user),
    media_queries: MediaQueries = Depends(get_media_queries),
):
    media = await media_queries.get_by_id(str(media_id))
    if not media or (str(media.user_id) != str(current_user.id) and current_user.role != UserRole.ADMIN):
        raise HTTPException(status_code=404, detail="Media not found or not authorized")
    return jsonable_encoder(media)
