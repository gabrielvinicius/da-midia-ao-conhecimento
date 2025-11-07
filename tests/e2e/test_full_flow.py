import pytest
from httpx import AsyncClient
from src.user_management.bootstrap import build_user_management_module, UserManagementModule
from src.user_management.api.dependencies import get_auth_dependencies
from main import lifespan, create_app

@pytest.mark.asyncio
async def test_full_video_summary_flow(client: AsyncClient, clean_db, auth_module: UserManagementModule):
    # Registra um usuário
    response = await client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "securepassword123"
    })
    assert response.status_code == 201
    user_id = response.json()["id"]

    # Login
    response = await client.post("/auth/token", data={
        "username": "test@example.com",
        "password": "securepassword123"
    })
    token = response.json()["access_token"]

    # Upload de vídeo
    with open("tests/sample.mp4", "rb") as file:
        response = await client.post(
            "/videos/upload",
            files={"file": ("sample.mp4", file, "video/mp4")},
            headers={"Authorization": f"Bearer {token}"}
        )
    assert response.status_code == 200
    video_id = response.json()["video_id"]

    # Verifica o status do vídeo (polling ou mock de eventos)
    response = await client.get(f"/videos/{video_id}", headers={"Authorization": f"Bearer {token}"})
    assert response.json()["status"] == "COMPLETED"

    # Verifica o resumo
    response = await client.get(f"/summaries/{video_id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert len(response.json()["summary"]) > 0

    # Verifica a notificação (mock SMTP)
    response = await client.get(f"/notifications?user_id={user_id}", headers={"Authorization": f"Bearer {token}"})
    assert any(n["type"] == "EMAIL" for n in response.json())