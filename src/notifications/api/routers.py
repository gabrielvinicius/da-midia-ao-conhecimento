# src/notifications/api/routers.py
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from typing import List

from src.auth.api.dependencies import get_current_user, get_current_user_from_token
from src.auth.domain.user import User
from .dependencies import (
    get_notification_service,
    get_notification_queries,
    get_connection_manager,
)

from src.notifications.application.notification_service import NotificationService
from src.notifications.application.queries.notification_queries import NotificationQueries
from src.notifications.infrastructure.connection_manager import ConnectionManager
from .schemas import NotificationResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/", response_model=List[NotificationResponse], summary="Get all notifications for the current user")
async def get_notifications(
    queries: NotificationQueries = Depends(get_notification_queries),
    current_user: User = Depends(get_current_user),
):
    """Retrieves all notifications for the currently authenticated user."""
    notifications = await queries.list_by_user(str(current_user.id))
    return notifications


@router.post("/{notification_id}/read", response_model=NotificationResponse, summary="Mark a notification as read")
async def mark_as_read(
    notification_id: str,
    service: NotificationService = Depends(get_notification_service),
    current_user: User = Depends(get_current_user),
):
    """Marks a specific notification as read."""
    try:
        notification = await service.mark_as_read(notification_id, str(current_user.id))
        return notification
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    manager: ConnectionManager = Depends(get_connection_manager),
    user: User = Depends(get_current_user_from_token),
):
    """Establishes a WebSocket connection for real-time notifications for the authenticated user."""
    user_id = str(user.id)
    await manager.connect(user_id, websocket)
    try:
        while True:
            # Keep the connection alive. The client can send pings or the server can.
            # For this implementation, we just wait for the client to disconnect.
            await websocket.receive_text() 
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
        print(f"Client #{user_id} disconnected from notifications WebSocket.")
