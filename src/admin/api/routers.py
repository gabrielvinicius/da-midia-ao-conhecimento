# src/admin/api/routers.py
from fastapi import APIRouter, Depends, Query, HTTPException, status, Request
from typing import Optional, List, Annotated, Any
from uuid import UUID
from jose import JWTError, jwt

# --- Local Dependency Injection and Security Logic ---

from src.auth.domain.user import User, UserRole
from src.auth.config.settings import AuthSettings
from src.auth.application.queries.auth_queries import AuthQueries
from src.auth.infrastructure.oauth2_scheme import oauth2_scheme
from src.media_management.application.queries.media_queries import MediaQueries
from src.admin.application.queries.admin_queries import AdminQueries
from src.auth.application.auth_service import AuthService
from src.media_management.application.media_service import MediaService
from src.auth.api.schemas import UserResponse
from src.media_management.api.schemas import MediaResponse
from .schemas import UserUpdateRequest, SystemStatsResponse

def get_container(request: Request) -> dict:
    return request.app.state.container

def get_auth_service(container: Annotated[dict, Depends(get_container)]) -> AuthService:
    return container["auth_service"]

def get_media_service(container: Annotated[dict, Depends(get_container)]) -> MediaService:
    return container["media_service"]

def get_auth_queries(container: Annotated[dict, Depends(get_container)]) -> AuthQueries:
    return container["auth_queries"]

def get_media_queries(container: Annotated[dict, Depends(get_container)]) -> MediaQueries:
    return container["media_queries"]

def get_admin_queries(container: Annotated[dict, Depends(get_container)]) -> AdminQueries:
    return container["admin_queries"]

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

async def get_current_admin_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if current_user.role != UserRole.ADMIN: raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")
    return current_user

# --- Router Definition ---

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(get_current_admin_user)]
)

# --- Endpoints ---

@router.get("/stats", response_model=SystemStatsResponse)
async def get_system_stats(queries: AdminQueries = Depends(get_admin_queries)):
    return await queries.get_global_stats()

@router.get("/users", response_model=List[UserResponse])
async def list_all_users(
    queries: AuthQueries = Depends(get_auth_queries),
    page: int = Query(1, ge=1), limit: int = Query(10, ge=1, le=100), search: Optional[str] = None
):
    return await queries.list_all(page=page, limit=limit, search=search)

@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: UUID, data: UserUpdateRequest, service: AuthService = Depends(get_auth_service)):
    try:
        return await service.update_user(user_id, role=data.role)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: UUID, service: AuthService = Depends(get_auth_service)):
    try:
        await service.delete_user(user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/media", response_model=List[MediaResponse])
async def list_all_media(
    queries: MediaQueries = Depends(get_media_queries),
    page: int = Query(1, ge=1), limit: int = Query(10, ge=1, le=100), search: Optional[str] = None
):
    return await queries.list_all(page=page, limit=limit, search=search)

@router.delete("/media/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media(media_id: UUID, service: MediaService = Depends(get_media_service)):
    try:
        await service.delete_media(media_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/media/{media_id}/reprocess", status_code=status.HTTP_202_ACCEPTED)
async def reprocess_media(media_id: UUID, service: MediaService = Depends(get_media_service)):
    try:
        await service.reprocess_media(media_id)
        return {"message": "Reprocessing initiated."}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
