# src/shared/validation/schemas.py
"""Sistema centralizado de validação com Pydantic v2.
Esquemas reutilizáveis e validadores customizados.
"""

import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
)
from pydantic.types import conint

from src.shared.infrastructure.logging import get_logger

logger = get_logger("validation")


# === Tipos Base Customizados ===
from typing import Annotated

from pydantic import StringConstraints

StrictStr = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]
SafeFilename = Annotated[str, StringConstraints(pattern=r'^[a-zA-Z0-9._-]+$', min_length=1, max_length=255)]
SecurePassword = Annotated[str, StringConstraints(min_length=8, max_length=128)]


# === Enums de Validação ===

class MediaTypeEnum(str, Enum):
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    TEXT = "TEXT"


class MediaStatusEnum(str, Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class UserRoleEnum(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class NotificationTypeEnum(str, Enum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    WEBHOOK = "WEBHOOK"


# === Esquemas Base ===

class BaseSchema(BaseModel):
    """Esquema base com configurações padrão."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        arbitrary_types_allowed=False,
        use_enum_values=True
    )


class TimestampMixin(BaseModel):
    """Mixin para campos de timestamp."""

    created_at: Optional[datetime] = Field(default=None, description="Data de criação")
    updated_at: Optional[datetime] = Field(default=None, description="Data de atualização")


class PaginationParams(BaseSchema):
    """Parâmetros de paginação padronizados."""

    page: conint(ge=1) = Field(default=1, description="Número da página")
    limit: conint(ge=1, le=100) = Field(default=10, description="Itens por página")
    order_by: Optional[str] = Field(default="created_at", description="Campo para ordenação")
    order_desc: bool = Field(default=True, description="Ordenação descendente")


class SearchParams(BaseSchema):
    """Parâmetros de busca padronizados."""

    search: Optional[StrictStr] = Field(default=None, description="Termo de busca")

    @field_validator('search')
    def validate_search_term(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v.strip()) < 2:
            raise ValueError("Termo de busca deve ter pelo menos 2 caracteres")
        return v


# === Esquemas de Usuário ===

class UserBase(BaseSchema):
    """Esquema base para usuário."""

    email: str = Field(..., description="Email do usuário")

    @field_validator('email')
    def validate_email_domain(cls, v: str) -> str:
        # Lista de domínios temporários para bloquear
        blocked_domains = {'10minutemail.com', 'tempmail.org', 'guerrillamail.com'}
        domain = v.split('@')[1].lower()

        if domain in blocked_domains:
            raise ValueError(f"Domínio de email temporário não permitido: {domain}")

        return v


class UserCreate(UserBase):
    """Esquema para criação de usuário."""

    password: SecurePassword = Field(..., description="Senha do usuário")
    confirm_password: str = Field(..., description="Confirmação da senha")

    @field_validator('confirm_password')
    def passwords_match(cls, v: str, info: ValidationInfo) -> str:
        password = info.data.get('password')
        if password is not None and v != password:
            raise ValueError('Senhas não coincidem')
        return v

    @field_validator('password')
    def validate_password_strength(cls, v: str) -> str:
        """Validação robusta de força da senha."""
        errors = []

        if not re.search(r'[A-Z]', v):
            errors.append("deve conter pelo menos uma letra maiúscula")

        if not re.search(r'[a-z]', v):
            errors.append("deve conter pelo menos uma letra minúscula")

        if not re.search(r'\d', v):
            errors.append("deve conter pelo menos um número")

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            errors.append("deve conter pelo menos um caractere especial")

        if errors:
            raise ValueError(f"Senha {', '.join(errors)}")

        return v


class UserUpdate(BaseSchema):
    """Esquema para atualização de usuário."""

    email: Optional[str] = None
    role: Optional[UserRoleEnum] = None


class UserResponse(UserBase, TimestampMixin):
    """Esquema de resposta para usuário."""

    id: UUID = Field(..., description="ID único do usuário")
    role: UserRoleEnum = Field(..., description="Papel do usuário")
    is_active: bool = Field(default=True, description="Usuário ativo")

    model_config = ConfigDict(**BaseSchema.model_config, from_attributes=True)


# === Esquemas de Mídia ===

class MediaBase(BaseSchema):
    """Esquema base para mídia."""

    media_type: MediaTypeEnum = Field(..., description="Tipo da mídia")
    language: Optional[str] = Field(default=None, description="Idioma da mídia")

    @field_validator('language')
    def validate_language_code(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.match(r'^[a-z]{2}(-[A-Z]{2})?$', v):
            raise ValueError("Código de idioma deve estar no formato ISO 639-1 (ex: 'pt', 'en-US')")
        return v


class MediaCreate(MediaBase):
    """Esquema para criação de mídia."""

    storage_provider: StrictStr = Field(default="local", description="Provedor de storage")
    transcription_provider: Optional[StrictStr] = Field(default=None, description="Provedor de transcrição")
    summarization_provider: Optional[StrictStr] = Field(default=None, description="Provedor de resumo")

    @field_validator('storage_provider')
    def validate_storage_provider(cls, v: str) -> str:
        allowed_providers = {'local', 's3', 'gcs', 'azure'}
        if v not in allowed_providers:
            raise ValueError(f"Provedor de storage deve ser um de: {allowed_providers}")
        return v


class MediaUpdate(BaseSchema):
    """Esquema para atualização de mídia."""

    status: Optional[MediaStatusEnum] = None
    error_message: Optional[str] = Field(default=None, max_length=1000)


class MediaResponse(MediaBase, TimestampMixin):
    """Esquema de resposta para mídia."""

    id: UUID = Field(..., description="ID único da mídia")
    user_id: UUID = Field(..., description="ID do usuário proprietário")
    original_file_path: str = Field(..., description="Caminho do arquivo original")
    status: MediaStatusEnum = Field(..., description="Status do processamento")
    error_message: Optional[str] = Field(default=None, description="Mensagem de erro se houver")
    storage_provider: str = Field(..., description="Provedor de storage utilizado")

    model_config = ConfigDict(**BaseSchema.model_config, from_attributes=True)


class MediaListResponse(BaseSchema):
    """Resposta paginada para lista de mídias."""

    items: List[MediaResponse] = Field(..., description="Lista de mídias")
    total: int = Field(..., description="Total de itens")
    page: int = Field(..., description="Página atual")
    limit: int = Field(..., description="Itens por página")
    total_pages: int = Field(..., description="Total de páginas")

    @field_validator('total_pages', mode='after')
    def calculate_total_pages(cls, v: int, info: ValidationInfo) -> int:
        total = info.data.get('total')
        limit = info.data.get('limit')
        if total is not None and limit:
            return (total + limit - 1) // limit
        return v


# === Esquemas de Autenticação ===

class LoginRequest(BaseSchema):
    """Esquema para requisição de login."""

    username: str = Field(..., description="Email do usuário")
    password: str = Field(..., min_length=1, description="Senha do usuário")


class TokenResponse(BaseSchema):
    """Esquema de resposta para token."""

    access_token: str = Field(..., description="Token de acesso")
    token_type: str = Field(default="bearer", description="Tipo do token")
    csrf_token: Optional[str] = Field(default=None, description="Token CSRF")
    expires_in: Optional[int] = Field(default=None, description="Tempo de expiração em segundos")


class ChangePasswordRequest(BaseSchema):
    """Esquema para mudança de senha."""

    old_password: str = Field(..., min_length=1, description="Senha atual")
    new_password: SecurePassword = Field(..., description="Nova senha")
    confirm_new_password: str = Field(..., description="Confirmação da nova senha")

    @field_validator('confirm_new_password')
    def passwords_match(cls, v: str, info: ValidationInfo) -> str:
        new_password = info.data.get('new_password')
        if new_password is not None and v != new_password:
            raise ValueError('Nova senha e confirmação não coincidem')
        return v


# === Esquemas de Notificação ===

class NotificationBase(BaseSchema):
    """Esquema base para notificação."""

    title: StrictStr = Field(..., max_length=200, description="Título da notificação")
    message: StrictStr = Field(..., max_length=1000, description="Mensagem da notificação")
    notification_type: NotificationTypeEnum = Field(..., description="Tipo de notificação")


class NotificationCreate(NotificationBase):
    """Esquema para criação de notificação."""

    user_id: UUID = Field(..., description="ID do usuário destinatário")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Metadados adicionais")


class NotificationResponse(NotificationBase, TimestampMixin):
    """Esquema de resposta para notificação."""

    id: UUID = Field(..., description="ID único da notificação")
    user_id: UUID = Field(..., description="ID do usuário destinatário")
    is_read: bool = Field(default=False, description="Notificação foi lida")
    read_at: Optional[datetime] = Field(default=None, description="Data de leitura")

    model_config = ConfigDict(**BaseSchema.model_config, from_attributes=True)


# === Validadores Customizados ===

def validate_file_upload(file_data: bytes, allowed_extensions: List[str], max_size_mb: int = 100) -> bool:
    """Valida upload de arquivo."""
    # Verificar tamanho
    if len(file_data) > max_size_mb * 1024 * 1024:
        raise ValueError(f"Arquivo muito grande. Tamanho máximo: {max_size_mb}MB")

    # Verificar se não está vazio
    if len(file_data) == 0:
        raise ValueError("Arquivo está vazio")

    logger.debug("File validation passed",
                size_bytes=len(file_data),
                max_size_mb=max_size_mb)

    return True


def validate_uuid_string(uuid_str: str) -> UUID:
    """Valida e converte string para UUID."""
    try:
        return UUID(uuid_str)
    except ValueError:
        raise ValueError(f"'{uuid_str}' não é um UUID válido")


# === Esquemas de Erro ===

class ErrorDetail(BaseSchema):
    """Detalhe de erro padronizado."""

    field: Optional[str] = Field(default=None, description="Campo que causou o erro")
    message: str = Field(..., description="Mensagem de erro")
    code: Optional[str] = Field(default=None, description="Código do erro")


class ErrorResponse(BaseSchema):
    """Resposta de erro padronizada."""

    error: str = Field(..., description="Código do erro")
    message: str = Field(..., description="Mensagem principal")
    details: List[ErrorDetail] = Field(default=[], description="Detalhes dos erros")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp do erro")


# === Utility Functions ===

def create_validation_error_response(validation_errors: List[Dict[str, Any]]) -> ErrorResponse:
    """Cria resposta de erro a partir de erros de validação do Pydantic."""
    details = []
    for error in validation_errors:
        details.append(ErrorDetail(
            field='.'.join(str(loc) for loc in error.get('loc', [])),
            message=error.get('msg', 'Erro de validação'),
            code=error.get('type', 'validation_error')
        ))

    return ErrorResponse(
        error="VALIDATION_ERROR",
        message="Dados de entrada inválidos",
        details=details
    )
