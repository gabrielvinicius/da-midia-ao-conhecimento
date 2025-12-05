"""Unit tests for LocalStorageService asynchronous operations."""

from pathlib import Path

import pytest

from src.storage.infrastructure.local_storage_service import LocalStorageService
from src.storage.domain.value_objects.file_path import FilePath


@pytest.mark.asyncio
async def test_local_storage_round_trip(tmp_path: Path):
    storage = LocalStorageService(tmp_path)
    file_name = FilePath("test_folder/test.txt")
    content = b"hello, world!"

    assert not await storage.exists(file_name)

    metadata = await storage.store(file_name, content)
    assert await storage.exists(file_name)
    assert metadata.size.bytes == len(content)

    downloaded_bytes = await storage.retrieve(file_name)
    assert downloaded_bytes == content
    
    deleted = await storage.remove(file_name)
    assert deleted
    assert not await storage.exists(file_name)