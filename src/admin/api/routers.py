# src/admin/api/routers.py
from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import Optional
from uuid import UUID

from src.auth.api.dependencies import get_current_admin_user
from src.auth.application.auth_service import AuthService
from src.auth.application.queries.auth_queries import AuthQueries
from src.media_management.application.media_service import MediaService # Import MediaService
from src.media_management.application.queries.media_queries import MediaQueries
from src.admin.application.queries.admin_queries import AdminQueries
from src.auth.api.schemas import UserResponse
from src.media_management.api.schemas import MediaResponse
from src.shared.api.schemas import PaginatedResponse

from .dependencies import get_auth_queries, get_media_queries, get_admin_queries, get_auth_service, get_media_service # Import getter

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(get_current_admin_user)]
)


@router.get("/stats", summary="Get system-wide statistics")
async def get_system_stats(
    admin_queries: AdminQueries = Depends(get_admin_queries),
):
    """Retrieves aggregated statistics for the entire system."""
    stats = await admin_queries.get_global_stats()
    return stats


@router.get("/users", response_model=PaginatedResponse[UserResponse], summary="List all users in the system with pagination")
async def list_all_users(
    auth_queries: AuthQueries = Depends(get_auth_queries),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term for user email")
):
    paginated_users = await auth_queries.list_all(page=page, limit=limit, search=search)
    return paginated_users


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a user")
async def delete_user(
    user_id: UUID,
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        await auth_service.delete_user(user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return


@router.get("/media", response_model=PaginatedResponse[MediaResponse], summary="List all media in the system with pagination")
async def list_all_media(
    media_queries: MediaQueries = Depends(get_media_queries),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term for media filename")
):
    paginated_media = await media_queries.list_all(page=page, limit=limit, search=search)
    return paginated_media


@router.delete("/media/{media_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a media item")
async def delete_media(
    media_id: UUID,
    media_service: MediaService = Depends(get_media_service),
):
    """Deletes a media item and its associated file from storage."""
    try:
        await media_service.delete_media(media_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return
