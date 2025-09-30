# src/admin/api/routers.py
from fastapi import APIRouter, Depends
from typing import List

from src.auth.api.dependencies import get_current_admin_user
from src.auth.application.queries.auth_queries import AuthQueries
from src.media_management.application.queries.media_queries import MediaQueries
from src.auth.api.schemas import UserResponse
from src.media_management.api.schemas import MediaResponse

from .dependencies import get_auth_queries, get_media_queries

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(get_current_admin_user)]
)


@router.get("/stats", summary="Get system-wide statistics")
async def get_system_stats():
    """Retrieves aggregated statistics for the entire system."""
    # Placeholder: Implementation will follow.
    return {"total_users": 0, "total_media": 0, "processing_media": 0}


@router.get("/users", response_model=List[UserResponse], summary="List all users in the system")
async def list_all_users(
    auth_queries: AuthQueries = Depends(get_auth_queries),
):
    """Retrieves a list of all users."""
    users = await auth_queries.list_all()
    return users


@router.get("/media", response_model=List[MediaResponse], summary="List all media in the system")
async def list_all_media(
    media_queries: MediaQueries = Depends(get_media_queries),
):
    """Retrieves a list of all media items from all users."""
    all_media = await media_queries.list_all()
    return all_media
