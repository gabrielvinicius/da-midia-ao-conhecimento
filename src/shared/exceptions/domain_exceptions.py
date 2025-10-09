# src/shared/exceptions/domain_exceptions.py
"""
Sistema centralizado de exceções de domínio para a aplicação.
Fornece hierarquia clara de erros e tratamento padronizado.
"""

from typing import Optional, Dict, Any
from datetime import datetime


class DomainException(Exception):
    """Exceção base para todos os erros de domínio da aplicação."""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__.upper()
        self.details = details or {}
        self.timestamp = datetime.utcnow().isoformat()
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte a exceção para um dicionário para serialização."""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp
        }


# === Exceções de Validação ===

class ValidationError(DomainException):
    """Erro de validação de dados de entrada."""
    
    def __init__(self, field: str, value: Any, reason: str):
        super().__init__(
            f"Validation failed for field '{field}': {reason}",
            error_code="VALIDATION_ERROR",
            details={"field": field, "value": str(value), "reason": reason}
        )


class BusinessRuleViolationError(DomainException):
    """Violação de regra de negócio."""
    
    def __init__(self, rule: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            f"Business rule violation: {rule}",
            error_code="BUSINESS_RULE_VIOLATION",
            details={"rule": rule, "context": context or {}}
        )


# === Exceções de Recursos ===

class ResourceNotFoundError(DomainException):
    """Recurso não encontrado."""
    
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            f"{resource_type} with ID '{resource_id}' not found",
            error_code="RESOURCE_NOT_FOUND",
            details={"resource_type": resource_type, "resource_id": resource_id}
        )


class ResourceAlreadyExistsError(DomainException):
    """Recurso já existe."""
    
    def __init__(self, resource_type: str, identifier: str):
        super().__init__(
            f"{resource_type} with identifier '{identifier}' already exists",
            error_code="RESOURCE_ALREADY_EXISTS",
            details={"resource_type": resource_type, "identifier": identifier}
        )


# === Exceções de Autenticação e Autorização ===

class AuthenticationError(DomainException):
    """Erro de autenticação."""
    
    def __init__(self, reason: str = "Invalid credentials"):
        super().__init__(
            f"Authentication failed: {reason}",
            error_code="AUTHENTICATION_ERROR",
            details={"reason": reason}
        )


class AuthorizationError(DomainException):
    """Erro de autorização."""
    
    def __init__(self, action: str, resource: Optional[str] = None):
        message = f"Not authorized to perform action: {action}"
        if resource:
            message += f" on resource: {resource}"
            
        super().__init__(
            message,
            error_code="AUTHORIZATION_ERROR",
            details={"action": action, "resource": resource}
        )


# === Exceções de Mídia e Processamento ===

class MediaNotFoundError(ResourceNotFoundError):
    """Mídia não encontrada."""
    
    def __init__(self, media_id: str):
        super().__init__("Media", media_id)


class MediaProcessingError(DomainException):
    """Erro no processamento de mídia."""
    
    def __init__(self, media_id: str, stage: str, reason: str):
        super().__init__(
            f"Media processing failed at stage '{stage}': {reason}",
            error_code="MEDIA_PROCESSING_ERROR",
            details={
                "media_id": media_id,
                "stage": stage,
                "reason": reason
            }
        )


class UnsupportedMediaTypeError(DomainException):
    """Tipo de mídia não suportado."""
    
    def __init__(self, media_type: str, supported_types: list):
        super().__init__(
            f"Media type '{media_type}' is not supported. Supported types: {', '.join(supported_types)}",
            error_code="UNSUPPORTED_MEDIA_TYPE",
            details={
                "media_type": media_type,
                "supported_types": supported_types
            }
        )


# === Exceções de Sistema ===

class ExternalServiceError(DomainException):
    """Erro em serviço externo."""
    
    def __init__(self, service_name: str, operation: str, reason: str):
        super().__init__(
            f"External service '{service_name}' failed during '{operation}': {reason}",
            error_code="EXTERNAL_SERVICE_ERROR",
            details={
                "service_name": service_name,
                "operation": operation,
                "reason": reason
            }
        )


class ConfigurationError(DomainException):
    """Erro de configuração."""
    
    def __init__(self, setting: str, reason: str):
        super().__init__(
            f"Configuration error for setting '{setting}': {reason}",
            error_code="CONFIGURATION_ERROR",
            details={"setting": setting, "reason": reason}
        )


# === Exceções de Rate Limiting ===

class RateLimitExceededError(DomainException):
    """Rate limit excedido."""
    
    def __init__(self, resource: str, limit: int, window: str):
        super().__init__(
            f"Rate limit exceeded for '{resource}': {limit} requests per {window}",
            error_code="RATE_LIMIT_EXCEEDED",
            details={
                "resource": resource,
                "limit": limit,
                "window": window
            }
        )


# === Exceções de Storage ===

class StorageError(DomainException):
    """Erro de storage."""
    
    def __init__(self, operation: str, reason: str, file_path: Optional[str] = None):
        super().__init__(
            f"Storage operation '{operation}' failed: {reason}",
            error_code="STORAGE_ERROR",
            details={
                "operation": operation,
                "reason": reason,
                "file_path": file_path
            }
        )