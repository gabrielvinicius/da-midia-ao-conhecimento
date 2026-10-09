import os

import pytest
from httpx import AsyncClient

from src.user_management.domain import User


LIGHTWEIGHT = os.getenv("LIGHTWEIGHT_BOOTSTRAP", "0") == "1"


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Test the root endpoint."""
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "message": "Media Processing API",
        "version": "2.0.0",
        "status": "operational",
        "docs": "/docs",
        "health": "/health",
    }


@pytest.mark.asyncio
async def test_health_check_endpoint(client: AsyncClient, monkeypatch):
    """A rota /health da aplicação é a que verifica banco e Redis."""
    from src.shared.infrastructure.observability.health import health_check as health

    async def ok():
        return True

    monkeypatch.setattr(health, "CHECKS", {"database": ok, "redis": ok})
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "database": "connected", "redis": "connected"}


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    """Test user registration."""
    response = await client.post(
        "/auth/register",
        json={"email": "novo@example.com", "password": "Password123"},
    )
    assert response.status_code == 201
    assert response.json()["email"] == "novo@example.com"


@pytest.mark.asyncio
async def test_register_cannot_grant_admin_role(client: AsyncClient):
    """Um visitante não pode se cadastrar como administrador."""
    response = await client.post(
        "/auth/register",
        json={"email": "intruso@example.com", "password": "Password123", "role": "ADMIN"},
    )
    assert response.status_code == 201
    assert response.json()["role"] == "USER"


@pytest.mark.asyncio
async def test_register_duplicate_email_is_rejected(client: AsyncClient):
    """O e-mail do usuário semeado já existe."""
    response = await client.post(
        "/auth/register",
        json={"email": "test@example.com", "password": "Password123"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_with_wrong_password_is_rejected(client: AsyncClient):
    """Sem atalho de teste: senha errada não autentica."""
    response = await client.post(
        "/auth/token",
        data={"username": "test@example.com", "password": "Errada123"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_for_access_token(client: AsyncClient, authenticated_user: User):
    """Test login for access token."""
    response = await client.post(
        "/auth/token",
        data={"username": "test@example.com", "password": "Password123"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_read_users_me(client: AsyncClient, authenticated_user: User):
    """Test reading the current user."""
    response = await client.get("/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_upload_media(client: AsyncClient, authenticated_user: User):
    """Test uploading media."""
    response = await client.post(
        "/media/",
        files={"file": ("test.txt", b"test content", "text/plain")},
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_upload_media_in_parts(client: AsyncClient, authenticated_user: User):
    """Envio em partes (arquivos acima do limite por requisição da Cloudflare)."""
    started = await client.post("/media/uploads", json={"filename": "notas.txt", "size_bytes": 12})
    assert started.status_code == 201
    upload_id = started.json()["upload_id"]

    first = await client.put(f"/media/uploads/{upload_id}", params={"offset": 0}, content=b"test ")
    assert first.json()["offset"] == 5
    assert (await client.put(f"/media/uploads/{upload_id}", params={"offset": 9}, content=b"x")).status_code == 409
    assert (await client.put(f"/media/uploads/{upload_id}", params={"offset": 5}, content=b"content")).json()[
        "offset"
    ] == 12

    completed = await client.post(f"/media/uploads/{upload_id}/complete")
    assert completed.status_code == 201
    assert completed.json()["filename"] == "notas.txt"
    assert (await client.get(f"/media/uploads/{upload_id}")).status_code == 404


@pytest.mark.asyncio
async def test_list_media_by_several_statuses(client: AsyncClient, authenticated_user: User):
    """O painel filtra "em andamento" (enviada, em processamento, em análise) numa consulta só."""
    await client.post("/media/", files={"file": ("test.txt", b"test content", "text/plain")})

    in_progress = await client.get("/media/", params=[("status", "uploaded"), ("status", "processing")])
    completed = await client.get("/media/", params={"status": "completed"})

    assert in_progress.json()["total"] == 1
    assert completed.json()["items"] == []
    assert (await client.get("/media/", params={"status": "inexistente"})).status_code == 422


@pytest.mark.asyncio
async def test_get_media(client: AsyncClient, authenticated_user: User):
    """Test getting media."""
    response = await client.post(
        "/media/",
        files={"file": ("test.txt", b"test content", "text/plain")},
    )
    media_id = response.json()["id"]
    response = await client.get(f"/media/{media_id}")
    assert response.status_code == 200


@pytest.mark.skip(reason="Depends on background task completion not synchronized in this test.")
@pytest.mark.asyncio
async def test_get_transcription(client: AsyncClient, authenticated_user: User):
    """Test getting a transcription."""
    response = await client.post(
        "/media/",
        files={"file": ("test.txt", b"test content", "text/plain")},
    )
    media_id = response.json()["id"]
    response = await client.get(f"/transcriptions/?media_id={media_id}")
    assert response.status_code == 200
