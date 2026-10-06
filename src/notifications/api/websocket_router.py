"""WebSocket dos avisos em tempo real.

O worker publica cada aviso no Redis; a ponte da API (redis_pubsub_bridge) o
repassa às conexões abertas aqui. Ao conectar, o usuário recebe o que chegou
com a página fechada. Antes, a rota ficava em main.py, chamava um método
inexistente (a conexão fechava logo após abrir) e havia aqui outra rota que
aceitava qualquer id de usuário sem token.
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from src.notifications.infrastructure.adapters.websockets.connection_manager import manager
from src.notifications.infrastructure.dependencies.builders import build_notification_service
from src.shared.infrastructure.database.db import AsyncSessionLocal
from src.user_management.api.dependencies import get_current_user_websocket
from src.user_management.domain import User

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.websocket("/ws/notifications")
async def notifications_socket(websocket: WebSocket, current_user: User = Depends(get_current_user_websocket)):
    user_id = str(current_user.id)
    await manager.connect(user_id, websocket)
    try:
        # Sessão curta: a conexão dura horas e não deve prender o banco.
        async with AsyncSessionLocal() as session:
            await build_notification_service(session).deliver_pending(
                current_user.id, lambda message: manager.send_to_user(user_id, message)
            )
        while True:
            await websocket.receive_text()  # o cliente só mantém a conexão viva
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(user_id, websocket)
        logger.info("notifications.socket_closed", user_id=user_id)


__all__ = ["router"]
