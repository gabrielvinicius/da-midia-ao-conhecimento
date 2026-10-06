"""A exclusão da pasta de uma mídia apaga os arquivos e não sai da raiz."""
import asyncio

import pytest

from src.storage.application.services.storage_service import StorageService
from src.storage.infrastructure.persistence.local_storage_repository import LocalStorageService


def test_delete_folder_removes_media_files(tmp_path):
    service = StorageService(LocalStorageService(tmp_path))
    asyncio.run(service.store_file("u1/2026/10/m1/aula.mp4", b"video"))
    asyncio.run(service.store_file("u1/2026/10/m2/outra.mp4", b"video"))

    assert asyncio.run(service.delete_folder("u1/2026/10/m1")) is True
    assert not (tmp_path / "u1/2026/10/m1").exists()
    assert (tmp_path / "u1/2026/10/m2/outra.mp4").exists()
    # Repetir não é erro: a exclusão interrompida pode ser refeita.
    assert asyncio.run(service.delete_folder("u1/2026/10/m1")) is False


@pytest.mark.parametrize("path", ["..", "../fora", "", "u1/../.."])
def test_delete_folder_refuses_paths_outside_root(tmp_path, path):
    root = tmp_path / "storage"
    service = StorageService(LocalStorageService(root))
    with pytest.raises(ValueError):
        asyncio.run(service.delete_folder(path))
    assert tmp_path.exists() and root.exists()
