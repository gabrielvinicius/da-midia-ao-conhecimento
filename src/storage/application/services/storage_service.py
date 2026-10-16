"""Application Service for Storage Operations."""
from typing import List, Optional

import structlog

from src.storage.application.ports import StorageRepositoryPort
from src.storage.domain.entities.file_metadata import FileMetadata
from src.storage.domain.value_objects.file_path import FilePath

logger = structlog.get_logger(__name__)


class StorageService:
    """Service for managing file storage operations.
    Orchestrates interactions with the StorageRepository.
    """

    def __init__(self, repository: StorageRepositoryPort):
        self._repository = repository

    async def store_file(self, path: str, content: bytes) -> FileMetadata:
        """Stores a file."""
        file_path = FilePath.from_path(path)
        logger.info("storage.store_file", path=str(file_path), size=len(content))
        return await self._repository.store(file_path, content)

    async def retrieve_file(self, path: str) -> Optional[bytes]:
        """Retrieves a file."""
        file_path = FilePath.from_path(path)
        return await self._repository.retrieve(file_path)

    async def store_file_from(self, path: str, source_path: str, *, move: bool = False) -> FileMetadata:
        """Grava a partir de um arquivo local (envios de até 500 MB); com
        ``move``, a origem é consumida."""
        file_path = FilePath.from_path(path)
        logger.info("storage.store_file", path=str(file_path), move=move)
        return await self._repository.store_from(file_path, source_path, move=move)

    async def read_file_range(self, path: str, start: int, end: int) -> Optional[bytes]:
        """Trecho do arquivo (para o reprodutor), sem lê-lo inteiro."""
        return await self._repository.read_range(FilePath.from_path(path), start, end)

    async def download_file_to(self, path: str, destination: str) -> bool:
        """Grava o arquivo em disco sem passar pela memória."""
        return await self._repository.download_to(FilePath.from_path(path), destination)

    async def delete_file(self, path: str) -> bool:
        """Deletes a file."""
        file_path = FilePath.from_path(path)
        logger.info("storage.delete_file", path=str(file_path))
        return await self._repository.remove(file_path)

    async def delete_folder(self, path: str) -> bool:
        """Deletes a folder and everything in it (e.g. all files of a media)."""
        logger.info("storage.delete_folder", path=path)
        return await self._repository.remove_folder(path)

    async def file_exists(self, path: str) -> bool:
        """Checks if file exists."""
        file_path = FilePath.from_path(path)
        return await self._repository.exists(file_path)

    async def get_file_metadata(self, path: str) -> Optional[FileMetadata]:
        """Gets file metadata."""
        file_path = FilePath.from_path(path)
        return await self._repository.get_metadata(file_path)

    async def list_files(self, prefix: str = "") -> List[str]:
        """Lists files matching prefix."""
        return await self._repository.list_files(prefix)
