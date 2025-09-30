# src/admin/api/routers.py
from fastapi import APIRouter, Depends, Query
from typing import Optional

from src.auth.api.dependencies import get_current_admin_user
from src.auth.application.queries.auth_queries import AuthQueries
from src.media_management.application.queries.media_queries import MediaQueries
from src.auth.api.schemas import UserResponse
from src.media_management.api.schemas import MediaResponse
from src.shared.api.schemas import PaginatedResponse

from .dependencies import get_auth_queries, get_media_queries

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(get_current_admin_user)]
)


@router.get("/stats", summary="Get system-wide statistics")
async def get_system_stats():
    """Retrieves aggregated statistics for the entire system."""
    return {"total_users": 0, "total_media": 0, "processing_media": 0}


@router.get("/users", response_model=PaginatedResponse[UserResponse], summary="List all users in the system with pagination")
async def list_all_users(
    auth_queries: AuthQueries = Depends(get_auth_queries),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term for user email")
):
    """Retrieves a paginated list of all users, with an option to search by email."""
    paginated_users = await auth_queries.list_all(page=page, limit=limit, search=search)
    return paginated_users


@router.get("/media", response_model=PaginatedResponse[MediaResponse], summary="List all media in the system with pagination")
async def list_all_media(
    media_queries: MediaQueries = Depends(get_media_queries),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term for media filename")
):
    """Retrieves a paginated list of all media items, with an option to search by filename."""
    paginated_media = await media_queries.list_all(page=page, limit=limit, search=search)
    return paginated_media
