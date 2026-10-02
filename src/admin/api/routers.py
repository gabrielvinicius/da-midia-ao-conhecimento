# src/admin/api/routers.py
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.admin.application.dtos import (
    GetMediaProcessingStatsQuery,
    GetSystemHealthQuery,
    GetSystemStatsQuery,
    GetUserActivityQuery,
)
from src.admin.application.services.admin_service import AdminService
from src.media_management.api.schemas import MediaResponse
from src.media_management.application.dtos import (
    ListMediaQuery,
)
from src.media_management.application.errors import MediaDataErasureError
from src.media_management.domain import MediaNotReprocessableError
from src.shared.application.schemas import PaginatedResponse
from src.user_management.api.dependencies import get_current_admin_user
from src.user_management.api.schemas import UserResponse
from src.user_management.application.dtos import ListUsersQuery
from src.user_management.domain import User

from .dependencies import (
    get_admin_service,
)
from .schemas import SystemStatsResponse, UserUpdateRequest

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(get_current_admin_user)] # Protect the entire router
)


@router.get(
    "/stats",
    response_model=SystemStatsResponse,
    summary="Get system-wide statistics",
)
async def get_system_stats(service: AdminService = Depends(get_admin_service)):
    """Retrieves global statistics about the system, such as total users, media, etc."""
    return await service.get_system_stats(GetSystemStatsQuery())


@router.get(
    "/users",
    response_model=PaginatedResponse[UserResponse],
    summary="List all users in the system",
)
async def list_all_users(
    service: AdminService = Depends(get_admin_service),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term for user email"),
):
    """Lists all users com paginação e busca."""
    result = await service.list_users(
        ListUsersQuery(page=page, limit=limit, search=search)
    )
    return PaginatedResponse[UserResponse](
        items=result["items"],
        total=result["total_items"],
        page=result["current_page"],
        pages=result["total_pages"],
        limit=limit,
    )


@router.put(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Update a user's role",
)
async def update_user(
    user_id: UUID,
    update_data: UserUpdateRequest,
    service: AdminService = Depends(get_admin_service),
    current_admin: User = Depends(get_current_admin_user),
):
    """Updates a user's role. Requires admin privileges."""
    try:
        return await service.update_user_role(
            user_id=user_id,
            new_role=update_data.role,
            admin_user=current_admin,
        )
    except (ValueError, PermissionError) as e:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if isinstance(e, ValueError)
            else status.HTTP_403_FORBIDDEN
        )
        raise HTTPException(status_code=status_code, detail=str(e))


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user",
)
async def delete_user(
    user_id: UUID,
    service: AdminService = Depends(get_admin_service),
    current_admin: User = Depends(get_current_admin_user),
):
    """Deletes a user from the system. Requires admin privileges."""
    try:
        await service.delete_user(
            user_id=user_id,
            admin_user=current_admin,
        )
    except (ValueError, PermissionError) as e:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if isinstance(e, ValueError)
            else status.HTTP_403_FORBIDDEN
        )
        raise HTTPException(status_code=status_code, detail=str(e))



@router.get(
    "/media",
    response_model=PaginatedResponse[MediaResponse],
    summary="List all media in the system",
)
async def list_all_media(
    service: AdminService = Depends(get_admin_service),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(
        None, description="Search term for media filename"
    ),
):
    """Lists all media items with pagination and search capabilities."""
    result = await service.list_media(
        ListMediaQuery(page=page, limit=limit, search=search)
    )

    if isinstance(result, dict):
        total = result.get("total", 0)
        items = result.get("items", [])
    else:
        total = getattr(result, "total", 0)
        items = getattr(result, "items", [])

    total_pages = (total + limit - 1) // limit if limit else 1

    return PaginatedResponse[MediaResponse](
        items=items,
        total=total,
        page=page,
        pages=total_pages,
        limit=limit,
    )


@router.delete(
    "/media/{media_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a media item",
)
async def delete_media(
    media_id: UUID,
    service: AdminService = Depends(get_admin_service),
    current_admin: User = Depends(get_current_admin_user),
):
    """Deletes a media item and its associated files from storage."""
    try:
        await service.delete_media(
            media_id=media_id,
            admin_user=current_admin,
        )
    except MediaDataErasureError as e:
        # Nada foi apagado pela metade sem aviso: a operação pode ser repetida.
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except (ValueError, PermissionError) as e:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if isinstance(e, ValueError)
            else status.HTTP_403_FORBIDDEN
        )
        raise HTTPException(status_code=status_code, detail=str(e))


@router.post(
    "/media/{media_id}/reprocess",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Reprocess a failed media item",
)
async def reprocess_media(
    media_id: UUID,
    service: AdminService = Depends(get_admin_service),
    current_admin: User = Depends(get_current_admin_user),
):
    """Triggers reprocessing for a media item that previously failed."""
    try:
        await service.reprocess_media(
            media_id=media_id,
            admin_user=current_admin,
        )
        return {"message": "Reprocessing initiated."}
    except MediaDataErasureError as e:
        # Nada foi apagado pela metade sem aviso: a operação pode ser repetida.
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except MediaNotReprocessableError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except (ValueError, PermissionError) as e:
        status_code = (
            status.HTTP_400_BAD_REQUEST
            if isinstance(e, ValueError)
            else status.HTTP_403_FORBIDDEN
        )
        raise HTTPException(status_code=status_code, detail=str(e))


# New enhanced admin routes using SOLID refactored services

@router.get("/stats/health", summary="Get system health status")
async def get_system_health(service: AdminService = Depends(get_admin_service)):
    """Get comprehensive system health status."""
    return await service.get_system_health(GetSystemHealthQuery())


@router.get(
    "/stats/processing-times",
    summary="Durações de transcrição e de cada etapa da análise",
)
async def get_processing_times(
    days: Optional[int] = Query(None, ge=1, le=365, description="Últimos N dias; vazio = tudo."),
    service: AdminService = Depends(get_admin_service),
):
    """Execuções, falhas, média, mediana, máximo e fator de tempo real por tarefa."""
    return await service.get_processing_times(days)


@router.get(
    "/stats/media-processing",
    summary="Get detailed media processing statistics",
)
async def get_media_processing_stats(
    service: AdminService = Depends(get_admin_service),
):
    """Get detailed media processing statistics."""
    return await service.get_media_processing_stats(GetMediaProcessingStatsQuery())


@router.get("/users/{user_id}/activity", summary="Get user activity statistics")
async def get_user_activity(
    user_id: UUID,
    service: AdminService = Depends(get_admin_service),
    current_admin: User = Depends(get_current_admin_user),
):
    """Get activity statistics for a specific user."""
    try:
        return await service.get_user_activity(
            query=GetUserActivityQuery(user_id=user_id, admin_user_id=current_admin.id)
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/users/{user_id}/activate",
    response_model=UserResponse,
    summary="Activate user account",
)
async def activate_user(
    user_id: UUID,
    service: AdminService = Depends(get_admin_service),
    current_admin: User = Depends(get_current_admin_user),
):
    """Activate a user account."""
    try:
        return await service.activate_user(user_id=user_id, admin_user=current_admin)
    except (ValueError, PermissionError) as e:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if isinstance(e, ValueError)
            else status.HTTP_403_FORBIDDEN
        )
        raise HTTPException(status_code=status_code, detail=str(e))


@router.post(
    "/users/{user_id}/deactivate",
    response_model=UserResponse,
    summary="Deactivate user account",
)
async def deactivate_user(
    user_id: UUID,
    service: AdminService = Depends(get_admin_service),
    current_admin: User = Depends(get_current_admin_user),
):
    """Deactivate a user account."""
    try:
        return await service.deactivate_user(user_id=user_id, admin_user=current_admin)
    except (ValueError, PermissionError) as e:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if isinstance(e, ValueError)
            else status.HTTP_403_FORBIDDEN
        )
        raise HTTPException(status_code=status_code, detail=str(e))


@router.post("/media/bulk-reprocess", summary="Bulk reprocess all failed media")
async def bulk_reprocess_failed_media(
    service: AdminService = Depends(get_admin_service),
    current_admin: User = Depends(get_current_admin_user),
):
    """Reprocess all failed media items in bulk."""
    try:
        reprocessed_count = await service.bulk_reprocess_failed_media(
            admin_user=current_admin
        )
        return {
            "message": (
                f"Bulk reprocessing initiated for {reprocessed_count} media items"
            ),
            "reprocessed_count": reprocessed_count,
        }
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

