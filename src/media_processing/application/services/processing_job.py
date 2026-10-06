"""O que a transcrição e a extração de texto fazem igual ao começar.

Antes, cada serviço lia o arquivo inteiro para a memória (vídeos de até
500 MB) e o regravava num temporário; o vídeo ainda era regravado de novo
para extrair os quadros. Agora o armazenamento grava direto no disco, e o
mesmo arquivo serve à transcrição, à descrição dos quadros e à extração.
"""
from __future__ import annotations

import os
import tempfile
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator, Optional

from src.media_processing.application.ports import StoragePort
from src.shared.application.event_bus import SupportsEventBus
from src.shared.domain.errors import NotFoundError
from src.shared.domain.events import MediaProcessingStarted


@dataclass(frozen=True)
class StagedFile:
    path: str
    size_bytes: int


@asynccontextmanager
async def staged_file(storage: StoragePort, file_path: str) -> AsyncIterator[StagedFile]:
    """Cópia local do arquivo da mídia, apagada ao sair."""
    descriptor, local_path = tempfile.mkstemp(suffix=Path(file_path).suffix)
    os.close(descriptor)
    try:
        if not await storage.download_to(file_path, local_path):
            raise NotFoundError("Arquivo da mídia não encontrado no armazenamento.")
        yield StagedFile(local_path, os.path.getsize(local_path))
    finally:
        with suppress(FileNotFoundError):
            os.remove(local_path)


async def announce_started(
    event_bus: Optional[SupportsEventBus], media_id, stage: str, correlation_id: Optional[str]
) -> None:
    if event_bus:
        await event_bus.publish(
            MediaProcessingStarted(media_id=str(media_id), stage=stage, correlation_id=correlation_id)
        )


__all__ = ["StagedFile", "staged_file", "announce_started"]
