"""Leitura dos bytes de uma mídia para o reprodutor (com suporte a Range)."""
from __future__ import annotations

import re
import uuid
from typing import Optional, Tuple

import structlog

from src.media_management.application.dtos import GetMediaStreamQuery, MediaStreamDTO
from src.media_management.application.errors import InvalidRangeError
from src.media_management.application.policies import MediaAccessPolicy
from src.media_management.application.ports import MediaRepositoryPort, StorageDownloaderPort
from src.shared.domain.errors import NotFoundError, TemporarilyUnavailableError
from src.shared.domain.roles import UserRole

logger = structlog.get_logger(__name__)

RANGE_HEADER_PATTERN = re.compile(r"bytes=(\d+)-(\d+)?")


def byte_range(range_header: Optional[str], size: int) -> Optional[Tuple[int, int]]:
    """Intervalo pedido no cabeçalho Range (início e fim inclusivos), ou None."""
    if not range_header:
        return None
    match = RANGE_HEADER_PATTERN.match(range_header.strip())
    if not match:
        raise InvalidRangeError("Cabeçalho Range inválido")
    start = int(match.group(1))
    if start >= size:
        raise InvalidRangeError("Intervalo fora do arquivo")
    end = int(match.group(2)) if match.group(2) is not None else size - 1
    return start, min(end, size - 1)


class StreamMedia:
    def __init__(
        self,
        media_repository: MediaRepositoryPort,
        access_policy: MediaAccessPolicy,
        storage_downloader: Optional[StorageDownloaderPort],
    ) -> None:
        self._media = media_repository
        self._access = access_policy
        self._downloader = storage_downloader

    async def execute(
        self,
        query: GetMediaStreamQuery,
        user_id: Optional[uuid.UUID] = None,
        user_role: Optional[UserRole] = None,
    ) -> MediaStreamDTO:
        media = await self._media.get_by_id(query.media_id)
        if not media:
            raise NotFoundError("Mídia não encontrada")
        self._access.ensure_can_access(media, user_id, user_role)
        if not media.original_file_path:
            raise NotFoundError("Arquivo de mídia indisponível")
        if not self._downloader:
            raise RuntimeError("Storage downloader not configured")

        content = await self._download(media)
        size = len(content)
        headers = {
            "Accept-Ranges": "bytes",
            "Content-Disposition": f'inline; filename="{media.filename or media.original_file_path.split("/")[-1]}"',
        }
        requested = byte_range(query.range_header, size)
        if requested:
            start, end = requested
            content = content[start : end + 1]
            headers["Content-Range"] = f"bytes {start}-{end}/{size}"
        headers["Content-Length"] = str(len(content))
        return MediaStreamDTO(
            content=content,
            media_type=media.mime_type or "application/octet-stream",
            headers=headers,
            status_code=206 if requested else 200,
        )

    async def _download(self, media) -> bytes:
        provider = (media.storage_provider or "local").lower()
        try:
            content = await self._downloader.download(provider, media.original_file_path)
        except FileNotFoundError as exc:
            raise NotFoundError("Arquivo de mídia ausente no armazenamento") from exc
        except OSError as exc:  # armazenamento fora do ar: não é "arquivo ausente"
            logger.error("media.stream.download_failed", media_id=str(media.id), error=str(exc))
            raise TemporarilyUnavailableError("Armazenamento indisponível. Tente novamente.") from exc
        if not content:
            raise NotFoundError("Arquivo de mídia vazio")
        return content
