"""Download de um arquivo por link direto (vídeo, áudio, PDF, documento, imagem).

O servidor baixa de um endereço escolhido pelo usuário: sem cuidado, o link
poderia apontar para a rede interna (banco, Redis, Ollama, metadados da
nuvem). Cada endereço, inclusive os de redirecionamento, é resolvido e só
segue se todos os IPs forem públicos.
"""
from __future__ import annotations

import asyncio
import ipaddress
import mimetypes
import os
import re
import socket
from typing import Callable, Iterable, Optional
from urllib.parse import unquote, urljoin, urlparse

import httpx
import structlog

from src.media_management.application.errors import InvalidUploadError
from src.media_management.application.ports import FetchedMedia

logger = structlog.get_logger(__name__)

MAX_REDIRECTS = 5
CHUNK_BYTES = 1024 * 1024

# Tipos que o servidor informa, para links sem extensão no nome.
_EXTENSION_BY_TYPE = {
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
    "video/x-matroska": ".mkv",
    "video/x-msvideo": ".avi",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/wave": ".wav",
    "audio/mp4": ".m4a",
    "audio/x-m4a": ".m4a",
    "audio/aac": ".aac",
    "audio/ogg": ".ogg",
    "audio/flac": ".flac",
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "text/plain": ".txt",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/tiff": ".tiff",
    "image/bmp": ".bmp",
}

Resolver = Callable[[str, int], Iterable[str]]


def _resolve(host: str, port: int) -> list[str]:
    return [info[4][0] for info in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)]


def _filename_from_disposition(header: str) -> Optional[str]:
    match = re.search(r"filename\*=(?:UTF-8'')?([^;]+)", header, re.I) or re.search(
        r'filename="?([^";]+)"?', header, re.I
    )
    return unquote(match.group(1).strip().strip('"')) if match else None


def _safe_name(name: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', " ", name or "").strip(" .")
    return re.sub(r"\s+", " ", cleaned)[:150]


class DirectLinkFetcherAdapter:
    def __init__(
        self,
        max_bytes: int,
        allowed_extensions: Iterable[str],
        resolver: Resolver = _resolve,
        transport: Optional[httpx.BaseTransport] = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._max_bytes = max_bytes
        self._allowed = {e.lower().lstrip(".") for e in allowed_extensions}
        self._resolver = resolver
        self._transport = transport
        self._timeout = timeout_seconds

    async def fetch(self, url: str, target_dir: str) -> FetchedMedia:
        return await asyncio.to_thread(self._fetch, url, target_dir)

    def _fetch(self, url: str, target_dir: str) -> FetchedMedia:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; Sintese/2.0)"}
        with httpx.Client(transport=self._transport, timeout=self._timeout, headers=headers) as client:
            for _ in range(MAX_REDIRECTS + 1):
                self._check_public(url)
                try:
                    with client.stream("GET", url, follow_redirects=False) as response:
                        if response.is_redirect and response.headers.get("location"):
                            url = urljoin(url, response.headers["location"])
                            continue
                        return self._save(response, url, target_dir)
                except httpx.HTTPError as exc:
                    logger.warning("media_management.direct_link.failed", error=str(exc)[:200])
                    raise InvalidUploadError("Não foi possível baixar o arquivo do link.") from exc
        raise InvalidUploadError("O link redireciona demais.")

    def _check_public(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise InvalidUploadError("O link precisa começar com http:// ou https://.")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        try:
            addresses = list(self._resolver(parsed.hostname, port))
        except OSError as exc:
            raise InvalidUploadError("O endereço do link não existe.") from exc
        if not addresses or not all(ipaddress.ip_address(a.split("%")[0]).is_global for a in addresses):
            raise InvalidUploadError("Este endereço não é permitido.")

    def _save(self, response: httpx.Response, url: str, target_dir: str) -> FetchedMedia:
        if response.status_code >= 400:
            raise InvalidUploadError(
                "O arquivo do link não foi encontrado." if response.status_code == 404
                else f"O servidor do link recusou o download (erro {response.status_code})."
            )
        content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
        if content_type == "text/html":
            raise InvalidUploadError(
                "O link abre uma página, não um arquivo. Use o link direto para o arquivo "
                "(no Google Drive, o arquivo precisa estar compartilhado com qualquer pessoa)."
            )
        length = int(response.headers.get("content-length") or 0)
        if length > self._max_bytes:
            raise InvalidUploadError("O arquivo do link passa do tamanho máximo de envio.")
        filename = self._filename(response, url, content_type)
        path = os.path.join(target_dir, "download" + os.path.splitext(filename)[1])
        size = 0
        with open(path, "wb") as target:
            for chunk in response.iter_bytes(CHUNK_BYTES):
                size += len(chunk)
                if size > self._max_bytes:
                    raise InvalidUploadError("O arquivo do link passa do tamanho máximo de envio.")
                target.write(chunk)
        if not size:
            raise InvalidUploadError("O link não trouxe nenhum conteúdo.")
        return FetchedMedia(path=path, filename=filename, size_bytes=size)

    def _filename(self, response: httpx.Response, url: str, content_type: str) -> str:
        """Nome pelo cabeçalho, pelo endereço ou, sem extensão, pelo tipo informado."""
        name = _filename_from_disposition(response.headers.get("content-disposition", "")) or unquote(
            os.path.basename(urlparse(url).path)
        )
        stem, ext = os.path.splitext(_safe_name(name))
        if ext.lower().lstrip(".") not in self._allowed:
            ext = _EXTENSION_BY_TYPE.get(content_type) or mimetypes.guess_extension(content_type or "") or ext
        if ext.lower().lstrip(".") not in self._allowed:
            raise InvalidUploadError(
                "O link não é de um tipo aceito: use vídeo, áudio, PDF, DOCX, TXT ou imagem."
            )
        return (stem or "arquivo-do-link") + ext.lower()
