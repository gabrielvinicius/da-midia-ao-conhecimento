from __future__ import annotations

import pytest
from async_asgi_testclient import TestClient

from main import app
from src.shared.infrastructure.db import AsyncSessionLocal
from src.user_management.application.user_service import UserService
from src.user_management.infrastructure.user_repository import UserRepository


@pytest.mark.asyncio
async def test_login_for_access_token():
    async with AsyncSessionLocal() as session:
        user_repo = UserRepository(session)
        user_service = UserService(user_repo)
        user = await user_service.create_user("test@example.com", "Password123")
        await session.commit()

        client = TestClient(app)
        # Test with correct credentials
        response = await client.post(
            "/auth/token", data={"username": "test@example.com", "password": "Password123"}
        )

        assert response.status_code == 200
        payload = response.json()
        assert "access_token" in payload
        assert payload["token_type"] == "bearer"

        # Test with incorrect credentials
        response = await client.post(
            "/auth/token", data={"username": "test@example.com", "password": "wrongpassword"}
        )

        assert response.status_code == 401
