# src/media_management/api/routers.py
import asyncio
import os
import tempfile
from contextlib import asynccontextmanager, suppress
from typing import AsyncIterator, Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.media_management.application.errors import InvalidRangeError, InvalidUploadError
from src.media_management.config.settings import media_settings
from src.media_management.application.dtos import (
    CreateMediaCommand,
    DeleteMediaCommand,
    GetMediaQuery,
    GetMediaStatisticsQuery,
    GetMediaStreamQuery,
    ImportMediaCommand,
    ListMediaQuery,
    ReprocessMediaCommand,
)
from src.media_management.application.services.media_service import MediaService
from src.shared.infrastructure.middleware.correlation_middleware import correlation_id_of
from src.user_management.api.dependencies import get_current_user, get_current_user_for_media_stream
from src.user_management.domain import User

from .dependencies import get_media_service
from src.shared.api.schemas import PaginatedResponse

from .schemas import MediaResponse, MediaStatisticsResponse, media_page

UPLOAD_CHUNK_BYTES = 1024 * 1024


@asynccontextmanager
async def received_file(upload: UploadFile, max_bytes: int) -> AsyncIterator[tuple[str, int]]:
    """Grava o envio num temporário, em partes de 1 MB, e o apaga ao sair.

    Antes, o arquivo inteiro (até 500 MB) era lido para a memória da API. Um
    envio acima do limite é recusado durante a cópia, sem chegar a ocupar o
    disco por inteiro.
    """
    descriptor, path = tempfile.mkstemp(suffix=os.path.splitext(upload.filename or "")[1])
    size = 0
    try:
        with os.fdopen(descriptor, "wb") as target:
            while chunk := await upload.read(UPLOAD_CHUNK_BYTES):
                size += len(chunk)
                if size > max_bytes:
                    raise InvalidUploadError("Tamanho do arquivo excede o limite máximo")
                await asyncio.to_thread(target.write, chunk)
        yield path, size
    finally:
        with suppress(FileNotFoundError):
            os.remove(path)


router = APIRouter(
    prefix="/media",
    tags=["Media"],
)


@router.post(
    "/",
    response_model=MediaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enviar uma mídia"
)
async def create_media(
    request: Request,
    file: UploadFile = File(...),
    storage_provider: Optional[str] = Query("local"),
    transcription_provider: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    service: MediaService = Depends(get_media_service),
):
    async with received_file(file, media_settings.media_max_file_size_bytes) as (path, size):
        command = CreateMediaCommand(
            user_id=current_user.id,
            file_path=path,
            file_size_bytes=size,
            filename=file.filename,
            storage_provider=storage_provider,
            transcription_provider=transcription_provider,
            correlation_id=correlation_id_of(request),
        )
        # Erros de validação viram 400 nos tratadores globais; o resto, 500 sem
        # expor a mensagem interna.
        media = await service.create_media(command)
    return MediaResponse.from_domain(media)


class MediaImportRequest(BaseModel):
    url: str = Field(..., min_length=10, max_length=500, description="Link de um vídeo do YouTube.")
    storage_provider: str = "local"
    transcription_provider: Optional[str] = None


@router.get("/import", summary="Importação por link disponível?")
async def media_import_options(
    current_user: User = Depends(get_current_user),
    service: MediaService = Depends(get_media_service),
):
    return {"enabled": service.url_import.enabled, "max_minutes": media_settings.media_url_import_max_minutes}


@router.post(
    "/import",
    response_model=MediaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Importar um vídeo do YouTube",
)
async def import_media(
    body: MediaImportRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    service: MediaService = Depends(get_media_service),
):
    """Baixa o vídeo e segue como um envio comum (pode levar alguns minutos)."""
    media = await service.import_media_from_url(
        ImportMediaCommand(
            user_id=current_user.id,
            url=body.url,
            storage_provider=body.storage_provider,
            transcription_provider=body.transcription_provider,
            correlation_id=correlation_id_of(request),
        )
    )
    return MediaResponse.from_domain(media)


@router.get(
    "/",
    response_model=PaginatedResponse[MediaResponse],
    summary="Mídias do usuário",
)
async def list_user_media(
    current_user: User = Depends(get_current_user),
    service: MediaService = Depends(get_media_service),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    order: str = Query("desc", pattern="^(asc|desc)$"),
):
    query = ListMediaQuery(
        user_id=current_user.id,
        page=page,
        limit=limit,
        search=search,
        order=order,
    )
    return media_page(await service.list_media(query), page, limit)


@router.get(
    "/stats",
    response_model=MediaStatisticsResponse,
    summary="Estatísticas das mídias do usuário",
)
async def media_stats(
    current_user: User = Depends(get_current_user),
    service: MediaService = Depends(get_media_service),
):
    query = GetMediaStatisticsQuery(user_id=current_user.id)
    stats = await service.get_media_statistics(query)
    return stats


@router.get(
    "/{media_id}",
    response_model=MediaResponse,
    summary="Uma mídia pelo id",
)
async def get_media_by_id(
    media_id: UUID,
    current_user: User = Depends(get_current_user),
    service: MediaService = Depends(get_media_service),
):
    media = await service.get_accessible_media(
        GetMediaQuery(media_id=media_id), current_user.id, current_user.role
    )
    return MediaResponse.from_domain(media)


@router.delete(
    "/{media_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Excluir uma mídia",
)
async def delete_media(
    media_id: UUID,
    current_user: User = Depends(get_current_user),
    service: MediaService = Depends(get_media_service),
):
    # Mídia de outro usuário: a política de acesso responde 404.
    await service.delete_media(
        DeleteMediaCommand(media_id=media_id), user_id=current_user.id, user_role=current_user.role
    )


@router.get("/{media_id}/stream", summary="Bytes da mídia para o reprodutor (com Range)")
async def stream_media(
    media_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user_for_media_stream),
    service: MediaService = Depends(get_media_service),
):
    try:
        query = GetMediaStreamQuery(
            media_id=media_id,
            range_header=request.headers.get("range"),
        )
        stream_dto = await service.get_media_stream(
            query,
            user_id=current_user.id,
            user_role=current_user.role,
        )

        # Enviado em partes, lidas do armazenamento à medida que saem.
        return StreamingResponse(
            stream_dto.chunks,
            media_type=stream_dto.media_type,
            headers=stream_dto.headers,
            status_code=stream_dto.status_code,
        )
    except InvalidRangeError as exc:  # 416 é próprio do HTTP de streaming, não um erro de negócio
        raise HTTPException(status_code=416, detail=str(exc))


@router.post(
    "/{media_id}/reprocess",
    response_model=MediaResponse,
    summary="Reprocessar uma mídia que falhou",
)
async def reprocess_media(
    media_id: UUID,
    current_user: User = Depends(get_current_user),
    service: MediaService = Depends(get_media_service),
):
    """Apaga os resultados anteriores e processa a mídia de novo; devolve a
    mídia já em processamento. Mídia de outro usuário: 404."""
    media = await service.reprocess_media(
        ReprocessMediaCommand(media_id=media_id), user_id=current_user.id, user_role=current_user.role
    )
    return MediaResponse.from_domain(media)
