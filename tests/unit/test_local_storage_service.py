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


@pytest.mark.asyncio
async def test_store_from_with_move_renames_instead_of_copying(tmp_path: Path, monkeypatch):
    """A conclusão do envio em partes copiava 433 MB (2,5 s); no mesmo disco,
    mover é só trocar o nome."""
    from src.storage.infrastructure.persistence import local_storage_repository as module

    def _no_copy(*_args, **_kwargs):
        raise AssertionError("copiou em vez de mover")

    monkeypatch.setattr(module.shutil, "copyfile", _no_copy)
    source = tmp_path / ".envios-em-partes" / "envio.part"
    source.parent.mkdir()
    source.write_bytes(b"aula")
    storage = LocalStorageService(tmp_path)

    metadata = await storage.store_from(FilePath("u/m/aula.mp4"), str(source), move=True)

    assert not source.exists()
    assert (tmp_path / "u" / "m" / "aula.mp4").read_bytes() == b"aula"
    assert metadata.size.bytes == 4


@pytest.mark.asyncio
async def test_move_across_disks_copies_and_removes_the_source(tmp_path: Path, monkeypatch):
    import errno
    import os

    from src.storage.infrastructure.persistence import local_storage_repository as module

    def _other_disk(*_args, **_kwargs):
        raise OSError(errno.EXDEV, "Invalid cross-device link")

    monkeypatch.setattr(module.os, "replace", _other_disk)
    source = tmp_path / "envio.part"
    source.write_bytes(b"aula")
    storage = LocalStorageService(tmp_path / "midias")

    await storage.store_from(FilePath("u/aula.mp4"), str(source), move=True)

    assert not os.path.exists(source)
    assert (tmp_path / "midias" / "u" / "aula.mp4").read_bytes() == b"aula"


@pytest.mark.asyncio
async def test_store_from_without_move_keeps_the_source(tmp_path: Path):
    source = tmp_path / "temporario.bin"
    source.write_bytes(b"aula")
    storage = LocalStorageService(tmp_path / "midias")

    await storage.store_from(FilePath("u/aula.mp4"), str(source))

    assert source.read_bytes() == b"aula"
    assert (tmp_path / "midias" / "u" / "aula.mp4").read_bytes() == b"aula"
