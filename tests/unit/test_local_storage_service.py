"""Unit tests for LocalStorageService asynchronous operations."""

import asyncio
from pathlib import Path

import pytest

from src.storage.domain.value_objects.file_path import FilePath
from src.storage.infrastructure.persistence.local_storage_repository import (
    LocalStorageService,
)


@pytest.mark.asyncio
async def test_local_storage_round_trip(tmp_path: Path):
    # Avoid thread scheduling overhead in CI/strict mode
    asyncio_to_thread = asyncio.to_thread
    try:
        async def _immediate(fn, *a, **k):
            return fn(*a, **k)
        asyncio.to_thread = _immediate
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
    finally:
        asyncio.to_thread = asyncio_to_thread
