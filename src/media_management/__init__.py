"""Pacote `media_management`.

Este `__init__` deve permanecer leve e sem efeitos colaterais:
- não importa bootstraps (evita puxar FastAPI/infra ao importar modelos no Alembic);
- expõe apenas elementos estáveis do bounded context.
"""

from .application.services.media_service import MediaService

__all__ = [
    "MediaService",
]
