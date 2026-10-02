from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.media_management.domain.enums import MediaStatus


class CreateMediaCommand(BaseModel):
    """Dados necessários para fazer upload de um novo media."""

    model_config = ConfigDict(frozen=True)

    user_id: str | UUID = Field(..., description="ID do dono do media.")
    file: bytes = Field(..., description="Arquivo binário a ser armazenado.")
    filename: str = Field(..., description="Nome original do arquivo.")
    storage_provider: str = Field(..., description="Provider de storage escolhido.")
    transcription_provider: Optional[str] = Field(
        None, description="Provider de transcrição a utilizar."
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Metadados adicionais enviados pelo cliente."
    )


class DeleteMediaCommand(BaseModel):
    """Command para excluir um media."""

    model_config = ConfigDict(frozen=True)

    media_id: UUID = Field(..., description="ID do media a excluir.")


class ReprocessMediaCommand(BaseModel):
    """Command para reprocessar um media."""

    model_config = ConfigDict(frozen=True)

    media_id: UUID = Field(..., description="ID do media a reprocessar.")


class GetMediaQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    media_id: UUID = Field(..., description="ID do media para consulta.")


class ListMediaQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    page: int = Field(1, ge=1, description="Página de paginação.")
    limit: int = Field(10, ge=1, le=100, description="Itens por página.")
    order: str = Field("desc", pattern="^(asc|desc)$", description="Ordenação por created_at.")
    user_id: Optional[UUID] = Field(
        None, description="Filtra por usuário dono (opcional)."
    )
    status: Optional[MediaStatus] = Field(
        None, description="Filtra por status (opcional)."
    )
    search: Optional[str] = Field(
        None, description="Termo de busca por nome/metadata (opcional)."
    )


class GetMediaStatisticsQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    user_id: Optional[UUID] = Field(
        None, description="Usuário para estatística (None = global)."
    )


class GetMediaStreamQuery(BaseModel):
    """Consulta para obter stream de bytes de uma mídia."""

    model_config = ConfigDict(frozen=True)
    media_id: UUID
    range_header: Optional[str] = None


class MediaStreamDTO(BaseModel):
    """Resultado do processamento de stream, pronto para a camada de transporte."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    content: bytes
    media_type: str
    headers: Dict[str, str]
    status_code: int


class PaginatedMedia(BaseModel):
    """Envelope de paginação para listagem de mídias."""

    model_config = ConfigDict(frozen=True)

    items: list
    total: int
    page: int | None = None
    pages: int | None = None
    limit: int | None = None
