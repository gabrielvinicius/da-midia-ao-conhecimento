from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Protocol
from uuid import UUID

from src.media_management.application.dtos import ListMediaQuery, PaginatedMedia
from src.user_management.application.dtos import ListUsersQuery
from src.user_management.domain import UserRole, User


class MediaAdminPort(Protocol):
    """O módulo de mídias, visto pelo admin. As ações passam pelos casos de
    uso do próprio módulo (com as mesmas regras), com papel de administrador."""

    async def status_of(self, media_id: UUID) -> Optional[str]:
        """Estado atual da mídia, ou None se ela não existir."""
        ...

    async def delete_media(self, media_id: UUID, actor_id: UUID) -> None: ...

    async def reprocess_media(self, media_id: UUID, actor_id: UUID) -> None: ...

    async def failed_media_ids(self, limit: int) -> List[UUID]:
        """Até ``limit`` mídias com falha, das mais antigas para as mais novas."""
        ...

    async def list_media(self, query: ListMediaQuery) -> PaginatedMedia: ...

    async def filenames(self, media_ids: List[UUID]) -> Dict[UUID, Optional[str]]:
        """Nome do arquivo de cada mídia (as que não existem mais ficam de fora)."""
        ...


class UserAdminPort(Protocol):
    """Port to interact with the User Management context."""
    async def list_users(self, query: ListUsersQuery) -> dict: ...

    async def update_user_role(
        self,
        user_id: UUID,
        new_role: UserRole,
        admin_user: User,
    ) -> User: ...

    async def delete_user(self, user_id: UUID, admin_user: User) -> None: ...

    async def activate_user(self, user_id: UUID, admin_user: User) -> User: ...

    async def deactivate_user(self, user_id: UUID, admin_user: User) -> User: ...


class AdminMediaReadPort(Protocol):
    async def count_all(self) -> int: ...
    async def count_by_status(self, status, since=None) -> int: ...
    async def count_by_user(self, user_id: UUID) -> int: ...
    async def count_by_user_and_status(self, user_id: UUID, status) -> int: ...


class AdminUserReadPort(Protocol):
    async def count_all(self) -> int: ...
    async def count_active(self) -> int: ...
    async def get_user_by_id(self, query) -> object | None: ...


class QueueDepthPort(Protocol):
    """Tarefas esperando em cada fila do Celery (ainda não pegas por um worker)."""

    async def waiting_tasks(self) -> Optional[Dict[str, int]]:
        """Por nome de fila; None se o broker não responder."""
        ...


@dataclass(frozen=True)
class GpuStatus:
    memory_used_mb: float
    memory_total_mb: float
    utilization_percent: float


@dataclass(frozen=True)
class ServerStatus:
    """Máquina e serviços, do ponto de vista do administrador."""

    cpu_percent: float
    cpu_count: int
    ram_used_gb: float
    ram_total_gb: float
    gpu: Optional[GpuStatus]  # None: sem leitura recente do worker pesado
    pressure: str
    services: Dict[str, bool] = field(default_factory=dict)
    workers: List[str] = field(default_factory=list)
    loaded_models: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class TranscriptionQuality:
    transcriptions: int
    corrected_transcriptions: int
    segments_total: int
    segments_corrected: int


class QualityPort(Protocol):
    """Correções e avaliações feitas pelos usuários sobre a saída da IA."""

    async def analysis_quality(self): ...  # text_analysis.application.insights.AnalysisQualityReport

    async def transcription_quality(self) -> TranscriptionQuality: ...


class ServerStatusPort(Protocol):
    async def snapshot(self) -> ServerStatus: ...


class AdminAuditPort(Protocol):
    async def log_admin_action(
        self,
        admin_user,
        action: str,
        target_type: str,
        target_id: UUID,
        details: dict | None = None,
    ) -> None: ...



__all__ = [
    "MediaAdminPort",
    "UserAdminPort",
    "AdminMediaReadPort",
    "AdminUserReadPort",
    "AdminAuditPort",
    "QueueDepthPort",
    "GpuStatus",
    "ServerStatus",
    "ServerStatusPort",
    "QualityPort",
    "TranscriptionQuality",
]
