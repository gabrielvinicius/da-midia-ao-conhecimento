"""Integration smoke tests for the consolidated /media endpoints.

These tests override the media dependencies with in-memory stubs so we can
exercise the HTTP surface without relying on real storage/event bus plumbing.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Dict, List
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from main import app
from src.media_management.api.dependencies import (
    get_media_lifecycle_service,
    get_media_query_service,
    get_media_upload_service,
)
from src.media_management.domain.enums import MediaStatus, MediaType
from src.shared.api.dependencies import get_current_user
from src.user_management.domain.user import User, UserRole


class InMemoryMediaStore:
    def __init__(self) -> None:
        self._records: Dict[UUID, Dict[str, object]] = {}

    def add(self, record: Dict[str, object]) -> Dict[str, object]:
        self._records[record["id"]] = record
        return record

    def list_for_user(self, user_id: UUID) -> List[Dict[str, object]]:
        return [record for record in self._records.values() if record["user_id"] == user_id]

    def get(self, media_id: UUID, user_id: UUID) -> Dict[str, object]:
        record = self._records.get(media_id)
        if record is None or record["user_id"] != user_id:
            raise KeyError(media_id)
        return record


class StubMediaUploadService:
    def __init__(self, store: InMemoryMediaStore) -> None:
        self._store = store

    async def create_media(
        self,
        user_id: UUID,
        file_content: bytes,
        filename: str,
        storage_provider: str,
        transcription_provider: str | None = None,
        summarization_provider: str | None = None,
        metadata: Dict[str, object] | None = None,
    ) -> Dict[str, object]:
        media_id = uuid4()
        record = {
            "id": media_id,
            "user_id": user_id,
            "original_file_path": f"media/{user_id}/{media_id}/{filename}",
            "media_type": MediaType.VIDEO,
            "status": MediaStatus.UPLOADED,
            "created_at": datetime.now(timezone.utc),
            "filename": filename,
            "storage_provider": storage_provider,
            "transcription_provider": transcription_provider,
            "summarization_provider": summarization_provider,
            "metadata": metadata or {},
        }
        return self._store.add(record)


class StubMediaQueryService:
    def __init__(self, store: InMemoryMediaStore) -> None:
        self._store = store

    async def list_media_for_user(self, user_id: UUID) -> List[Dict[str, object]]:
        return self._store.list_for_user(user_id)

    async def get_media_for_user(self, media_id: UUID, user_id: UUID, user_role: UserRole) -> Dict[str, object]:
        return self._store.get(media_id, user_id)


class StubMediaLifecycleService:
    def __init__(self, store: InMemoryMediaStore) -> None:
        self._store = store

    async def reprocess_media(self, media_id: UUID, user_id: UUID, user_role: UserRole) -> None:
        record = self._store.get(media_id, user_id)
        record["status"] = MediaStatus.PROCESSING


@pytest.fixture(autouse=True)
def override_media_dependencies():
    store = InMemoryMediaStore()
    user = User(
        id=uuid4(),
        email="demo@example.com",
        password_hash="hashed",
        role=UserRole.USER,
        is_active=True,
    )

    upload_service = StubMediaUploadService(store)
    query_service = StubMediaQueryService(store)
    lifecycle_service = StubMediaLifecycleService(store)

    async def _current_user():
        return user

    app.dependency_overrides[get_current_user] = _current_user
    app.dependency_overrides[get_media_upload_service] = lambda: upload_service
    app.dependency_overrides[get_media_query_service] = lambda: query_service
    app.dependency_overrides[get_media_lifecycle_service] = lambda: lifecycle_service

    yield

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_media_upload_service, None)
    app.dependency_overrides.pop(get_media_query_service, None)
    app.dependency_overrides.pop(get_media_lifecycle_service, None)


@pytest.mark.anyio
async def test_upload_media():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/media/",
            files={"file": ("sample.mp4", io.BytesIO(b"fake bytes"), "video/mp4")},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "UPLOADED"


@pytest.mark.anyio
async def test_list_media_returns_uploaded_entries():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/media/",
            files={"file": ("seed.mp4", io.BytesIO(b"seed"), "video/mp4")},
        )
        response = await client.get("/media/")

    assert response.status_code == 200
    items = response.json()
    assert isinstance(items, list)
    assert items, "Expected at least one media item"
    assert items[0]["status"] in {"UPLOADED", "PROCESSING"}


@pytest.mark.anyio
async def test_get_media_details():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post(
            "/media/",
            files={"file": ("detail.mp4", io.BytesIO(b"detail"), "video/mp4")},
        )
        media_id = created.json()["id"]

        response = await client.get(f"/media/{media_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == media_id
    assert data["status"] in {"UPLOADED", "PROCESSING"}
