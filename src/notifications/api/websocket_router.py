"""WebSocket endpoints for real-time notifications."""
from uuid import UUID

from fastapi import Depends, WebSocket, WebSocketDisconnect

from src.notifications.infrastructure.connection_manager import manager
from src.shared.api.dependencies import get_current_user
from src.user_management.domain import User


async def websocket_endpoint(
    websocket: WebSocket, current_user: User = Depends(get_current_user)
):
    """WebSocket endpoint for real-time notifications."""
    user_id = current_user.id

    await manager.connect(user_id, websocket)

    try:
        while True:
            # Wait for messages from the client (currently unused)
            data = await websocket.receive_text()
            await websocket.send_text(f"Received: {data}")

    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
        print(f"WebSocket connection for user {user_id} closed")


async def websocket_endpoint_for_user(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for notifications for a specific user."""
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        await websocket.close(code=1003, reason="Invalid user ID format")
        return

    await manager.connect(user_uuid, websocket)

    try:
        while True:
            # Wait for messages from the client (currently unused)
            data = await websocket.receive_text()
            await websocket.send_text(f"Received: {data}")

    except WebSocketDisconnect:
        manager.disconnect(user_uuid, websocket)
        print(f"WebSocket connection for user {user_uuid} closed")
