"""Download de vídeos do YouTube com o yt-dlp."""
from __future__ import annotations

import asyncio
import os
import re

import structlog

from src.media_management.application.errors import InvalidUploadError
from src.media_management.application.ports import FetchedMedia

logger = structlog.get_logger(__name__)

# Até 720p em MP4: basta para a transcrição e a descrição dos quadros, e cabe
# no limite de envio por mais tempo de vídeo.
VIDEO_FORMAT = "bv*[height<=720][ext=mp4]+ba[ext=m4a]/b[height<=720][ext=mp4]/b[height<=720]/b"

_MESSAGES = (
    ("private", "O vídeo é privado."),
    ("sign in to confirm your age", "O vídeo tem restrição de idade e não pode ser baixado."),
    ("members-only", "O vídeo é exclusivo para membros do canal."),
    ("unavailable", "O vídeo não está disponível."),
    ("not available in your country", "O vídeo não está disponível nesta região."),
    ("max-filesize", "O vídeo passa do tamanho máximo de envio."),
)


def _safe_filename(title: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', " ", title or "").strip(" .")
    return (re.sub(r"\s+", " ", cleaned)[:120] or "video-do-youtube") + ".mp4"


def _friendly(message: str) -> str:
    lowered = message.lower()
    return next((text for key, text in _MESSAGES if key in lowered), "Não foi possível baixar o vídeo do YouTube.")


class YoutubeFetcherAdapter:
    def __init__(self, max_bytes: int, max_seconds: int) -> None:
        self._max_bytes = max_bytes
        self._max_seconds = max_seconds

    async def fetch(self, url: str, target_dir: str) -> FetchedMedia:
        return await asyncio.to_thread(self._fetch, url, target_dir)

    def _fetch(self, url: str, target_dir: str) -> FetchedMedia:
        import yt_dlp  # só quem importa vídeos carrega a biblioteca

        options = {
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "noplaylist": True,
            "format": VIDEO_FORMAT,
            "merge_output_format": "mp4",
            "outtmpl": os.path.join(target_dir, "%(id)s.%(ext)s"),
            "max_filesize": self._max_bytes,
        }
        try:
            with yt_dlp.YoutubeDL(options) as client:
                info = client.extract_info(url, download=False)
                self._check(info)
                info = client.extract_info(url, download=True)
                path = client.prepare_filename(info)
        except InvalidUploadError:
            raise
        except Exception as exc:  # yt_dlp.utils.DownloadError e afins
            logger.warning("media_management.url_import.failed", error=str(exc)[:300])
            raise InvalidUploadError(_friendly(str(exc))) from exc
        path = self._downloaded(path, target_dir)
        return FetchedMedia(path=path, filename=_safe_filename(info.get("title", "")), size_bytes=os.path.getsize(path))

    def _check(self, info: dict) -> None:
        if info.get("is_live") or info.get("live_status") in ("is_live", "is_upcoming"):
            raise InvalidUploadError("Transmissões ao vivo não podem ser importadas; tente quando o vídeo estiver gravado.")
        duration = info.get("duration") or 0
        if duration > self._max_seconds:
            raise InvalidUploadError(
                f"O vídeo tem {round(duration / 60)} min; o máximo é {self._max_seconds // 60} min."
            )

    @staticmethod
    def _downloaded(expected: str, target_dir: str) -> str:
        """O arquivo final (a junção de áudio e vídeo pode mudar a extensão)."""
        if os.path.exists(expected):
            return expected
        candidates = [os.path.join(target_dir, f) for f in os.listdir(target_dir) if not f.endswith(".part")]
        if not candidates:
            raise InvalidUploadError("Não foi possível baixar o vídeo do YouTube.")
        return max(candidates, key=os.path.getsize)
