"""Leitura dos bytes de uma mídia para o reprodutor (com suporte a Range)."""
from __future__ import annotations

import re
import uuid
from typing import AsyncIterator, Optional, Tuple
from urllib.parse import quote

import structlog

from src.media_management.application.dtos import GetMediaStreamQuery, MediaStreamDTO
from src.media_management.application.errors import InvalidRangeError
from src.media_management.application.policies import MediaAccessPolicy
from src.media_management.application.ports import MediaRepositoryPort, StorageDownloaderPort
from src.shared.domain.errors import NotFoundError, TemporarilyUnavailableError
from src.shared.domain.roles import UserRole

logger = structlog.get_logger(__name__)

RANGE_HEADER_PATTERN = re.compile(r"bytes=(\d+)-(\d+)?")
CHUNK_BYTES = 1024 * 1024


def content_disposition(filename: str) -> str:
    """Cabeçalho com o nome do arquivo codificado (RFC 6266/5987).

    O nome vinha cru entre aspas: aspas ou acentos no nome quebravam o
    cabeçalho.
    """
    fallback = "".join(c if c.isascii() and c.isprintable() and c not in '"\\' else "_" for c in filename) or "midia"
    return f"inline; filename=\"{fallback}\"; filename*=UTF-8''{quote(filename, safe='')}"


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

        provider = (media.storage_provider or "local").lower()
        size = await self._size(media, provider)
        requested = byte_range(query.range_header, size)
        start, end = requested or (0, size - 1)
        headers = {
            "Accept-Ranges": "bytes",
            "Content-Disposition": content_disposition(media.filename or media.original_file_path.split("/")[-1]),
            "Content-Length": str(end - start + 1),
        }
        if requested:
            headers["Content-Range"] = f"bytes {start}-{end}/{size}"
        return MediaStreamDTO(
            chunks=self._chunks(provider, media.original_file_path, start, end),
            media_type=media.mime_type or "application/octet-stream",
            headers=headers,
            status_code=206 if requested else 200,
        )

    async def _size(self, media, provider: str) -> int:
        try:
            size = await self._downloader.size(provider, media.original_file_path)
        except OSError as exc:  # armazenamento fora do ar: não é "arquivo ausente"
            logger.error("media.stream.download_failed", media_id=str(media.id), error=str(exc))
            raise TemporarilyUnavailableError("Armazenamento indisponível. Tente novamente.") from exc
        if size is None:
            raise NotFoundError("Arquivo de mídia ausente no armazenamento")
        if size == 0:
            raise NotFoundError("Arquivo de mídia vazio")
        return size

    async def _chunks(self, provider: str, path: str, start: int, end: int) -> AsyncIterator[bytes]:
        """Lê o intervalo pedido em partes de 1 MB, só quando o cliente as consome.

        Antes, cada pedido do reprodutor (são dezenas por vídeo) lia o arquivo
        inteiro para a memória da API e só depois recortava o trecho.
        """
        position = start
        while position <= end:
            last = min(position + CHUNK_BYTES - 1, end)
            data = await self._downloader.read_range(provider, path, position, last)
            if not data:
                logger.warning("media.stream.short_read", path=path, position=position)
                return
            yield data
            position += len(data)
