"""Unit tests for LocalStorageService asynchronous operations."""

from pathlib import Path

import pytest

from src.storage.infrastructure.local_storage_service import LocalStorageService


@pytest.mark.asyncio
async def test_local_storage_round_trip(tmp_path: Path):
    storage = LocalStorageService(tmp_path)
    file_name = "test_folder/test.txt"
    content = b"hello, world!"

    assert not await storage.exists(file_name)

    await storage.upload(file_name, content)
    assert await storage.exists(file_name)

    downloaded_bytes, downloaded_name = await storage.download(file_name)
    assert downloaded_bytes == content
    assert downloaded_name == "test.txt"

    deleted = await storage.delete(file_name)
    assert deleted
    assert not await storage.exists(file_name)
