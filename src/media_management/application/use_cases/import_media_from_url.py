"""Mídia a partir de um link do YouTube: baixa e segue como um envio comum."""
from __future__ import annotations

import re
import tempfile
from typing import Optional
from urllib.parse import parse_qs, urlparse

import structlog

from src.media_management.application.dtos import CreateMediaCommand, ImportMediaCommand
from src.media_management.application.errors import InvalidUploadError
from src.media_management.application.ports import RemoteMediaFetcherPort
from src.media_management.application.use_cases.upload_media import UploadMedia
from src.media_management.domain import Media
from src.shared.domain.errors import NotFoundError

logger = structlog.get_logger(__name__)

_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}
_SHORT_HOSTS = {"youtu.be", "www.youtu.be"}
_PATH_PREFIXES = ("/shorts/", "/live/", "/embed/", "/v/")


def youtube_video_url(url: str) -> str:
    """Endereço canônico do vídeo, ou InvalidUploadError.

    Só vídeos do YouTube: o servidor não baixa de qualquer endereço (evita que
    a API seja usada para acessar a rede interna) nem listas inteiras.
    """
    parsed = urlparse((url or "").strip())
    host = (parsed.hostname or "").lower()
    video_id: Optional[str] = None
    if parsed.scheme in ("http", "https"):
        if host in _SHORT_HOSTS:
            video_id = parsed.path.strip("/").split("/")[0]
        elif host in _YOUTUBE_HOSTS:
            if parsed.path == "/watch":
                video_id = (parse_qs(parsed.query).get("v") or [None])[0]
            else:
                prefix = next((p for p in _PATH_PREFIXES if parsed.path.startswith(p)), None)
                video_id = parsed.path[len(prefix):].split("/")[0] if prefix else None
    if not video_id or not _VIDEO_ID.match(video_id):
        raise InvalidUploadError("Link inválido: informe o endereço de um vídeo do YouTube.")
    return f"https://www.youtube.com/watch?v={video_id}"


class ImportMediaFromUrl:
    def __init__(self, fetcher: Optional[RemoteMediaFetcherPort], upload: UploadMedia, enabled: bool) -> None:
        self._fetcher = fetcher
        self._upload = upload
        self.enabled = bool(enabled and fetcher)

    async def execute(self, command: ImportMediaCommand) -> Media:
        if not self.enabled:
            raise NotFoundError("A importação por link não está disponível.")
        url = youtube_video_url(command.url)
        # O temporário some ao fim, com sucesso ou não; o envio copia o arquivo.
        with tempfile.TemporaryDirectory(prefix="importacao-") as target_dir:
            fetched = await self._fetcher.fetch(url, target_dir)
            logger.info("media_management.url_import.downloaded", size_bytes=fetched.size_bytes)
            return await self._upload.execute(
                CreateMediaCommand(
                    user_id=command.user_id,
                    file_path=fetched.path,
                    file_size_bytes=fetched.size_bytes,
                    filename=fetched.filename,
                    storage_provider=command.storage_provider,
                    transcription_provider=command.transcription_provider,
                    correlation_id=command.correlation_id,
                )
            )


__all__ = ["ImportMediaFromUrl", "youtube_video_url"]
