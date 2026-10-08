"""Mídia a partir de um link: vídeo do YouTube ou link direto para um arquivo
(vídeo, áudio, PDF, documento, imagem). Baixa e segue como um envio comum."""
from __future__ import annotations

import re
import tempfile
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

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
_DRIVE_FILE = re.compile(r"^/file/d/([A-Za-z0-9_-]{10,})")


def is_youtube(url: str) -> bool:
    host = (urlparse((url or "").strip()).hostname or "").lower()
    return host in _YOUTUBE_HOSTS or host in _SHORT_HOSTS


def youtube_video_url(url: str) -> str:
    """Endereço canônico do vídeo, ou InvalidUploadError (listas inteiras não)."""
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


def direct_link_url(url: str) -> str:
    """Link direto para um arquivo, já no formato de download.

    Links de compartilhamento do Google Drive e do Dropbox abrem uma página;
    viram o endereço que entrega o arquivo. Se o endereço é permitido (não
    aponta para a rede interna) quem verifica é o adaptador, que resolve o nome.
    """
    parsed = urlparse((url or "").strip())
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise InvalidUploadError("Link inválido: use um endereço que comece com http:// ou https://.")
    if parsed.username or parsed.password:
        raise InvalidUploadError("Links com usuário e senha não são aceitos.")
    host = parsed.hostname.lower()
    if host == "drive.google.com" and (match := _DRIVE_FILE.match(parsed.path)):
        return f"https://drive.google.com/uc?export=download&id={match.group(1)}"
    if host in ("www.dropbox.com", "dropbox.com"):
        query = {k: v for k, v in parse_qs(parsed.query).items() if k != "dl"}
        query["dl"] = ["1"]
        return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))
    return urlunparse(parsed._replace(fragment=""))


class ImportMediaFromUrl:
    def __init__(
        self,
        youtube_fetcher: Optional[RemoteMediaFetcherPort],
        direct_fetcher: Optional[RemoteMediaFetcherPort],
        upload: UploadMedia,
        enabled: bool,
    ) -> None:
        self._youtube = youtube_fetcher
        self._direct = direct_fetcher
        self._upload = upload
        self.enabled = bool(enabled and (youtube_fetcher or direct_fetcher))

    def _route(self, url: str) -> tuple[RemoteMediaFetcherPort, str]:
        if is_youtube(url):
            if not self._youtube:
                raise InvalidUploadError("A importação de vídeos do YouTube não está disponível.")
            return self._youtube, youtube_video_url(url)
        if not self._direct:
            raise InvalidUploadError("Só links do YouTube são aceitos.")
        return self._direct, direct_link_url(url)

    async def execute(self, command: ImportMediaCommand) -> Media:
        if not self.enabled:
            raise NotFoundError("A importação por link não está disponível.")
        fetcher, url = self._route(command.url)
        # O temporário some ao fim, com sucesso ou não; o envio copia o arquivo.
        with tempfile.TemporaryDirectory(prefix="importacao-") as target_dir:
            fetched = await fetcher.fetch(url, target_dir)
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


__all__ = ["ImportMediaFromUrl", "direct_link_url", "is_youtube", "youtube_video_url"]
