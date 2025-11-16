"""
WebSocket endpoints for real-time notifications.
Implements WebSocket endpoints that allow clients to connect and receive real-time updates.
"""
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect, Depends

from src.notifications.infrastructure.connection_manager import manager
from src.shared.api.dependencies import get_current_user
from src.user_management.domain.user import User


async def websocket_endpoint(websocket: WebSocket, current_user: User = Depends(get_current_user)):
    """
    WebSocket endpoint for real-time notifications.
    
    Clients connect to this endpoint to receive real-time updates about notifications.
    The connection is managed by the connection manager which handles connecting,
    disconnecting, and broadcasting messages to connected clients.
    
    Args:
        websocket: The WebSocket connection
        current_user: The authenticated user (from dependency)
    """
    user_id = current_user.id
    
    await manager.connect(user_id, websocket)
    
    try:
        while True:
            # Wait for messages from the client (though we may not use them in basic implementation)
            data = await websocket.receive_text()
            # For now, we just echo back or handle client messages as needed
            # In the future, this could handle commands from the client
            await websocket.send_text(f"Received: {data}")
            
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
        print(f"WebSocket connection for user {user_id} closed")


async def websocket_endpoint_for_user(websocket: WebSocket, user_id: str):
    """
    WebSocket endpoint for real-time notifications for a specific user.
    
    This allows connecting a WebSocket for a specific user by ID without
    requiring authentication through the usual dependency.
    
    Args:
        websocket: The WebSocket connection
        user_id: The target user ID as a string
    """
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        await websocket.close(code=1003, reason="Invalid user ID format")
        return
    
    await manager.connect(user_uuid, websocket)
    
    try:
        while True:
            # Wait for messages from the client (though we may not use them in basic implementation)
            data = await websocket.receive_text()
            # Echo back for now
            await websocket.send_text(f"Received: {data}")
            
    except WebSocketDisconnect:
        manager.disconnect(user_uuid, websocket)
        print(f"WebSocket connection for user {user_uuid} closed")