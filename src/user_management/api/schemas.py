"""Esquemas da API de autenticação e usuários."""
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from src.user_management.application.tokens import TokenPurpose


class UserCreate(BaseModel):
    email: EmailStr = Field(
        ...,
        description="The user's email address.",
        json_schema_extra={"example": "user@example.com"},
    )
    password: str = Field(
        ...,
        min_length=8,
        description="The user's password (min 8 characters).",
        json_schema_extra={"example": "a_strong_password"},
    )
    # Sem campo "role": o cadastro público sempre cria um usuário comum. O
    # perfil de administrador só é concedido pela área administrativa.


class TokenRequest(BaseModel):
    """Schema for requesting a token with username and password."""

    username: str = Field(
        ...,
        description="The user's email address.",
        json_schema_extra={"example": "user@example.com"},
    )
    password: str = Field(
        ...,
        description="The user's password.",
        json_schema_extra={"example": "a_strong_password"},
    )


class ChangePasswordRequest(BaseModel):
    """Schema for changing a user's password."""

    old_password: str = Field(..., description="The user's current password.")
    new_password: str = Field(
        ...,
        min_length=8,
        description="The user's new password (min 8 characters).",
    )


class Token(BaseModel):
    """Schema for the response containing the access token."""

    access_token: str = Field(
        ...,
        description="The JWT access token.",
        json_schema_extra={"example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."},
    )
    token_type: str = Field(
        ...,
        description="The type of the token.",
        json_schema_extra={"example": "bearer"},
    )


class UserResponse(BaseModel):
    """Schema for returning user information safely."""

    id: UUID = Field(
        ...,
        description="The unique identifier for the user.",
        json_schema_extra={"example": "f47ac10b-58cc-4372-a567-0e02b2c3d479"},
    )
    email: EmailStr = Field(
        ...,
        description="The user's email address.",
        json_schema_extra={"example": "user@example.com"},
    )
    role: str # Assuming role is a string representation

    model_config = ConfigDict(from_attributes=True)


class RegisterResponse(UserResponse):
    email_verification_required: bool = Field(
        False, description="A conta só entra depois de confirmar o e-mail pelo link enviado."
    )


class EmailRequest(BaseModel):
    email: EmailStr


class TokenAction(BaseModel):
    token: str = Field(..., min_length=20, max_length=2000)


class PasswordResetRequest(TokenAction):
    new_password: str = Field(..., min_length=8, max_length=200)


class AuthOptionsResponse(BaseModel):
    """O que a tela de login e de cadastro deve oferecer."""

    email_enabled: bool = Field(..., description="Confirmação do cadastro e recuperação de senha por e-mail.")


class ScopedTokenRequest(BaseModel):
    purpose: Literal[TokenPurpose.MEDIA_STREAM, TokenPurpose.NOTIFICATIONS] = Field(
        ..., description="media_stream (com resource = id da mídia) ou notifications."
    )
    resource: Optional[UUID] = None

    @model_validator(mode="after")
    def _stream_needs_media(self) -> "ScopedTokenRequest":
        if self.purpose == TokenPurpose.MEDIA_STREAM and self.resource is None:
            raise ValueError("Informe a mídia (resource) do token de reprodução.")
        return self


class ScopedTokenResponse(BaseModel):
    token: str
    expires_in: int
