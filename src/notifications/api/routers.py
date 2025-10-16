# src/notifications/api/routers.py
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query
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
    token: str = Query(...),
    manager: ConnectionManager = Depends(get_connection_manager),
):
    """Establishes a WebSocket connection for real-time notifications for the authenticated user."""
    try:
        # Manually authenticate user for WebSocket
        from src.auth.api.dependencies import get_auth_settings, get_auth_queries
        from jose import jwt, JWTError
        
        # Get dependencies manually since WebSocket doesn't support Depends for user auth
        container = websocket.app.state.container
        settings = container.get("auth_settings")
        queries = container.get("auth_queries")
        
        if not settings or not queries:
            await websocket.close(code=1011, reason="Service dependencies not available")
            return
        
        # Validate token
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            user_id = payload.get("sub")
            if not user_id:
                await websocket.close(code=1008, reason="Invalid token")
                return
        except JWTError:
            await websocket.close(code=1008, reason="Invalid token")
            return
        
        # Verify user exists
        user = await queries.get_by_id(user_id)
        if not user:
            await websocket.close(code=1008, reason="User not found")
            return
        
        # Accept connection and connect to manager
        await manager.connect(user_id, websocket)
        
        try:
            while True:
                # Keep the connection alive and handle client messages
                data = await websocket.receive_text()
                # Echo ping messages or handle other client requests
                if data == "ping":
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            manager.disconnect(user_id, websocket)
            print(f"Client #{user_id} disconnected from notifications WebSocket.")
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass
