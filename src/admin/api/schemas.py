"""Esquemas da API do administrador."""
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from src.media_management.api.schemas import MediaResponse
from src.user_management.domain import UserRole


class UserUpdateRequest(BaseModel):
    """Novo perfil do usuário (obrigatório: antes, vazio virava erro 400 confuso)."""

    role: UserRole


class SystemStatsResponse(BaseModel):
    """Schema for aggregated admin statistics."""

    total_users: int
    active_users: int
    total_media: int
    processing_media: int
    failed_media: int
    completed_media: int
    success_rate: float


class AdminMediaResponse(MediaResponse):
    owner_email: Optional[str] = Field(None, description="E-mail do dono da mídia.")


class QueueItemResponse(BaseModel):
    position: int = Field(..., description="Ordem de chegada entre as mídias em andamento.")
    media_id: UUID
    filename: Optional[str] = None
    media_type: str
    status: str
    owner_email: Optional[str] = None
    created_at: datetime
    stage_since: datetime = Field(..., description="Início da etapa atual.")
    stage_seconds: float
    stuck: bool = Field(..., description="Na etapa há mais tempo que o normal.")


class QueueResponse(BaseModel):
    items: List[QueueItemResponse]
    counts: Dict[str, int] = Field(..., description="Mídias por estado (uploaded, processing, analyzing).")
    broker: Optional[Dict[str, int]] = Field(
        None, description="Tarefas esperando em cada fila do Celery; vazio se o Redis não respondeu."
    )
    truncated: bool = Field(..., description="Há mais mídias em andamento do que as listadas.")


class GpuStatusResponse(BaseModel):
    memory_used_mb: float
    memory_total_mb: float
    utilization_percent: float


class ServerStatusResponse(BaseModel):
    cpu_percent: float
    cpu_count: int
    ram_used_gb: float
    ram_total_gb: float
    gpu: Optional[GpuStatusResponse] = Field(None, description="Vazio sem leitura recente do worker pesado.")
    pressure: str = Field(..., description="low, moderate, high ou critical.")
    services: Dict[str, bool]
    workers: List[str] = Field(..., description="Workers do Celery que responderam ao ping.")
    loaded_models: List[str] = Field(..., description="Modelos carregados no Ollama agora.")


class RatedComment(BaseModel):
    media_id: Optional[UUID] = None
    filename: Optional[str] = None
    score: int
    comment: Optional[str] = None
    created_at: Optional[datetime] = None


class CorrectedMedia(BaseModel):
    media_id: Optional[UUID] = None
    filename: Optional[str] = None
    parts: List[str]


class QualityResponse(BaseModel):
    analyses: int = Field(..., description="Análises gravadas.")
    corrected: Dict[str, int] = Field(..., description="Análises com cada parte corrigida (resumo, temas...).")
    useful: int = Field(..., description='Avaliações "útil".')
    not_useful: int = Field(..., description='Avaliações "não foi útil".')
    useful_share: Optional[float] = Field(None, description='% de "útil" entre as avaliações.')
    recent_comments: List[RatedComment]
    recent_corrections: List[CorrectedMedia]
    transcriptions: int
    corrected_transcriptions: int
    segments_total: int
    segments_corrected: int
