# src/admin/api/routers.py
from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import Optional, List
from uuid import UUID

from src.shared.api.dependencies import get_current_admin_user
from src.auth.application.queries.auth_queries import AuthQueries
from src.media_management.application.queries.media_queries import MediaQueries
from src.admin.application.queries.admin_queries import AdminQueries
from src.auth.domain.user import User
from src.auth.api.schemas import UserResponse
from src.media_management.api.schemas import MediaResponse
from .schemas import UserUpdateRequest, SystemStatsResponse

from .dependencies import (
    get_auth_queries, get_media_queries, get_admin_queries, 
    get_admin_user_service, get_admin_media_service
)
from src.admin.application.services.admin_user_service import AdminUserService
from src.admin.application.services.admin_media_service import AdminMediaService

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(get_current_admin_user)] # Protect the entire router
)


@router.get("/stats", response_model=SystemStatsResponse, summary="Get system-wide statistics")
async def get_system_stats(
    admin_queries: AdminQueries = Depends(get_admin_queries),
):
    """Retrieves global statistics about the system, such as total users, media, etc."""
    return await admin_queries.get_global_stats()


@router.get("/users", response_model=List[UserResponse], summary="List all users in the system")
async def list_all_users(
    auth_queries: AuthQueries = Depends(get_auth_queries),
    page: int = Query(1, ge=1, description="Page number"), 
    limit: int = Query(10, ge=1, le=100, description="Items per page"), 
    search: Optional[str] = Query(None, description="Search term for user email")
):
    """Lists all users with pagination and search capabilities."""
    return await auth_queries.list_all(page=page, limit=limit, search=search)


@router.put("/users/{user_id}", response_model=UserResponse, summary="Update a user's role")
async def update_user(
    user_id: UUID,
    update_data: UserUpdateRequest,
    admin_user_service: AdminUserService = Depends(get_admin_user_service),
    current_admin: User = Depends(get_current_admin_user),
):
    """Updates a user's role. Requires admin privileges."""
    try:
        return await admin_user_service.update_user_role(
            user_id=user_id, 
            new_role=update_data.role,
            admin_user=current_admin
        )
    except (ValueError, PermissionError) as e:
        status_code = status.HTTP_404_NOT_FOUND if isinstance(e, ValueError) else status.HTTP_403_FORBIDDEN
        raise HTTPException(status_code=status_code, detail=str(e))


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a user")
async def delete_user(
    user_id: UUID,
    admin_user_service: AdminUserService = Depends(get_admin_user_service),
    current_admin: User = Depends(get_current_admin_user),
):
    """Deletes a user from the system. Requires admin privileges."""
    try:
        await admin_user_service.delete_user(user_id, current_admin)
    except (ValueError, PermissionError) as e:
        status_code = status.HTTP_404_NOT_FOUND if isinstance(e, ValueError) else status.HTTP_403_FORBIDDEN
        raise HTTPException(status_code=status_code, detail=str(e))


@router.get("/media", response_model=List[MediaResponse], summary="List all media in the system")
async def list_all_media(
    media_queries: MediaQueries = Depends(get_media_queries),
    page: int = Query(1, ge=1), 
    limit: int = Query(10, ge=1, le=100), 
    search: Optional[str] = Query(None, description="Search term for media filename")
):
    """Lists all media items with pagination and search capabilities."""
    return await media_queries.list_all(page=page, limit=limit, search=search)


@router.delete("/media/{media_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a media item")
async def delete_media(
    media_id: UUID,
    admin_media_service: AdminMediaService = Depends(get_admin_media_service),
    current_admin: User = Depends(get_current_admin_user),
):
    """Deletes a media item and its associated files from storage."""
    try:
        await admin_media_service.delete_media(media_id, current_admin)
    except (ValueError, PermissionError) as e:
        status_code = status.HTTP_404_NOT_FOUND if isinstance(e, ValueError) else status.HTTP_403_FORBIDDEN
        raise HTTPException(status_code=status_code, detail=str(e))


@router.post("/media/{media_id}/reprocess", status_code=status.HTTP_202_ACCEPTED, summary="Reprocess a failed media item")
async def reprocess_media(
    media_id: UUID,
    admin_media_service: AdminMediaService = Depends(get_admin_media_service),
    current_admin: User = Depends(get_current_admin_user),
):
    """Triggers the reprocessing pipeline for a media item that has previously failed."""
    try:
        await admin_media_service.reprocess_media(media_id, current_admin)
        return {"message": "Reprocessing initiated."}
    except (ValueError, PermissionError) as e:
        status_code = status.HTTP_400_BAD_REQUEST if isinstance(e, ValueError) else status.HTTP_403_FORBIDDEN
        raise HTTPException(status_code=status_code, detail=str(e))


# New enhanced admin routes using SOLID refactored services

@router.get("/stats/health", summary="Get system health status")
async def get_system_health(
    admin_queries: AdminQueries = Depends(get_admin_queries),
):
    """Get comprehensive system health status."""
    return await admin_queries.get_system_health_status()


@router.get("/stats/media-processing", summary="Get detailed media processing statistics")
async def get_media_processing_stats(
    admin_queries: AdminQueries = Depends(get_admin_queries),
):
    """Get detailed media processing statistics."""
    return await admin_queries.get_media_processing_stats()


@router.get("/users/{user_id}/activity", summary="Get user activity statistics")
async def get_user_activity(
    user_id: UUID,
    admin_queries: AdminQueries = Depends(get_admin_queries),
):
    """Get activity statistics for a specific user."""
    try:
        return await admin_queries.get_user_activity_stats(user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/users/{user_id}/activate", response_model=UserResponse, summary="Activate user account")
async def activate_user(
    user_id: UUID,
    admin_user_service: AdminUserService = Depends(get_admin_user_service),
    current_admin: User = Depends(get_current_admin_user),
):
    """Activate a user account."""
    try:
        return await admin_user_service.activate_user(user_id, current_admin)
    except (ValueError, PermissionError) as e:
        status_code = status.HTTP_404_NOT_FOUND if isinstance(e, ValueError) else status.HTTP_403_FORBIDDEN
        raise HTTPException(status_code=status_code, detail=str(e))


@router.post("/users/{user_id}/deactivate", response_model=UserResponse, summary="Deactivate user account")
async def deactivate_user(
    user_id: UUID,
    admin_user_service: AdminUserService = Depends(get_admin_user_service),
    current_admin: User = Depends(get_current_admin_user),
):
    """Deactivate a user account."""
    try:
        return await admin_user_service.deactivate_user(user_id, current_admin)
    except (ValueError, PermissionError) as e:
        status_code = status.HTTP_404_NOT_FOUND if isinstance(e, ValueError) else status.HTTP_403_FORBIDDEN
        raise HTTPException(status_code=status_code, detail=str(e))


@router.post("/media/bulk-reprocess", summary="Bulk reprocess all failed media")
async def bulk_reprocess_failed_media(
    admin_media_service: AdminMediaService = Depends(get_admin_media_service),
    current_admin: User = Depends(get_current_admin_user),
):
    """Reprocess all failed media items in bulk."""
    try:
        reprocessed_count = await admin_media_service.bulk_reprocess_failed_media(current_admin)
        return {
            "message": f"Bulk reprocessing initiated for {reprocessed_count} media items",
            "reprocessed_count": reprocessed_count
        }
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/maintenance/cleanup-orphaned-files", summary="Clean up orphaned files")
async def cleanup_orphaned_files(
    admin_media_service: AdminMediaService = Depends(get_admin_media_service),
    current_admin: User = Depends(get_current_admin_user),
):
    """Clean up orphaned files in storage."""
    try:
        cleaned_count = await admin_media_service.cleanup_orphaned_files(current_admin)
        return {
            "message": f"Cleanup completed, {cleaned_count} orphaned files removed",
            "cleaned_count": cleaned_count
        }
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
