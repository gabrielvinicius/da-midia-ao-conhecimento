from __future__ import annotations

from dataclasses import dataclass
import datetime
from typing import Any, AsyncIterator, Dict, List, Optional, Protocol, Set
from uuid import UUID

from src.media_management.domain import Media
from src.shared.application.observability import MetricsPort



class MediaMetricsPort(MetricsPort, Protocol):
    ...


class EventBusPort(Protocol):
    async def publish(self, event: Any) -> None: ...


class MediaRepositoryPort(Protocol):
    async def get_by_id(self, media_id: UUID): ...
    async def save(self, media: Media): ...
    async def delete(self, media_id: UUID): ...
    async def update(self, media: Media): ...
    async def count_all(self) -> int: ...
    async def count_by_user(self, user_id: UUID) -> int: ...
    async def count_by_status(self, status, since=None): ...
    async def count_by_user_and_status(self, user_id: UUID, status): ...
    async def count_by_type(self, media_type): ...
    async def count_by_user_and_type(self, user_id: UUID, media_type): ...
    async def count_filtered(
        self,
        *,
        user_id: UUID | None = None,
        status: Any | None = None,
        search: str | None = None,
    ) -> int: ...
    async def list_paginated(
        self,
        page: int,
        limit: int,
        user_id: UUID | None = None,
        status: Any | None = None,
        search: str | None = None,
        order: str = "desc",
    ): ...


class RecoverableMediaPort(Protocol):
    async def list_waiting(
        self,
        created_before: datetime.datetime,
        limit: int = 50,
        after: Optional[Media] = None,
    ) -> List[Media]:
        """Mídias ainda enviadas ou em processamento, criadas antes do instante
        dado, da mais antiga para a mais nova; after continua depois dessa mídia."""
        ...

    async def update(self, media: Media): ...


class AnalyzingMediaPort(Protocol):
    async def list_analyzing_since_before(self, updated_before: datetime.datetime, limit: int) -> List[Media]:
        """Mídias em análise desde antes do instante dado, das mais antigas para as mais novas."""
        ...

    async def update(self, media: Media): ...


class AnalysisCompletionRecordsPort(Protocol):
    """Conclusões persistidas, consultadas sem acessar tabelas de outro módulo."""

    async def completed_media_ids(self, media_ids: Set[UUID]) -> Set[UUID]: ...


class ProcessingRecordsPort(Protocol):
    """Diz quais mídias já ganharam registro no processamento (transcrição ou extração)."""

    async def media_with_processing(self, media_ids: List[UUID]) -> Set[UUID]: ...

    async def media_with_finished_processing(
        self, media_ids: List[UUID], finished_before: datetime.datetime
    ) -> Set[UUID]:
        """As que têm processamento já encerrado (concluído ou com falha) antes do instante dado."""
        ...


class StoredFileRemoverPort(Protocol):
    """Remove os arquivos de uma mídia do armazenamento (implementado pelo módulo storage)."""

    async def delete_folder(self, provider_name: str, folder_path: str) -> None: ...

    async def delete_file(self, provider_name: str, path: str) -> None: ...


class MediaDataEraserPort(Protocol):
    """Apaga o que um módulo derivou de uma mídia (transcrição, análise...).

    Cada módulo implementa a sua, sobre os próprios dados; este módulo só
    conhece a lista. Deve ser idempotente: uma exclusão interrompida pode ser
    repetida.
    """

    name: str

    async def erase(self, media_id: UUID) -> None: ...


@dataclass
class UploadResult:
    destination_path: str
    metadata: Dict[str, Any]


@dataclass
class UploadMetadata:
    stored_path: str
    file_size: int
    hash_digest: Optional[str] = None


class StorageUploaderPort(Protocol):
    async def upload(
        self, command, media_id: UUID, content_type: str
    ) -> UploadResult: ...

    async def discard(self, command, destination_path: str) -> None:
        """Apaga um arquivo enviado cuja mídia não chegou a ser gravada."""
        ...


class StorageDownloaderPort(Protocol):
    """Leitura do arquivo para o reprodutor, por trechos: um vídeo de 500 MB
    nunca passa inteiro pela memória da API."""

    async def size(self, provider_name: str, path: str) -> Optional[int]:
        """Tamanho em bytes, ou None se o arquivo não existir."""
        ...

    async def read_range(self, provider_name: str, path: str, start: int, end: int) -> Optional[bytes]:
        """Bytes de ``start`` a ``end`` (inclusivos)."""
        ...


class UploadMetadataMapperPort(Protocol):
    def map(
        self,
        storage_metadata: Dict[str, Any],
        default_path: str,
        file_size: int,
    ) -> UploadMetadata: ...


@dataclass(frozen=True)
class FetchedMedia:
    """Arquivo baixado de um link, já num diretório temporário local."""

    path: str
    filename: str
    size_bytes: int


class RemoteMediaFetcherPort(Protocol):
    """Baixa o vídeo de um link para ``target_dir`` (InvalidUploadError se não der)."""

    async def fetch(self, url: str, target_dir: str) -> FetchedMedia: ...


@dataclass(frozen=True)
class StagedUpload:
    """Envio em partes em andamento: o arquivo cresce a cada parte recebida."""

    upload_id: UUID
    user_id: str
    filename: str
    size_bytes: int
    storage_provider: str
    transcription_provider: Optional[str]
    created_at: datetime.datetime
    received_bytes: int = 0


class UploadStagingPort(Protocol):
    """Área temporária dos envios em partes, até a conclusão ou o abandono."""

    async def create(self, upload: StagedUpload) -> None: ...

    async def get(self, upload_id: UUID) -> Optional[StagedUpload]:
        """O envio com o total já recebido, ou None se não existir."""
        ...

    async def write(self, upload_id: UUID, offset: int, chunks: AsyncIterator[bytes], max_bytes: int) -> int:
        """Grava a partir de ``offset`` (descarta o que houver depois dele) e
        devolve o total recebido; InvalidUploadError acima de ``max_bytes``."""
        ...

    def file_path(self, upload_id: UUID) -> str: ...

    async def remove(self, upload_id: UUID) -> None: ...

    async def remove_created_before(self, moment: datetime.datetime) -> int: ...
