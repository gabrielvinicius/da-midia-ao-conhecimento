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
async def test_health_check_endpoint(client: AsyncClient):
    """Test the health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_metrics_endpoint(client: AsyncClient):
    """Test the metrics endpoint."""
    response = await client.get("/metrics")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    """Test user registration."""
    response = await client.post(
        "/auth/register",
        json={"email": "test@example.com", "password": "Password123"},
    )
    assert response.status_code == 201
    assert response.json()["email"] == "test@example.com"


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
