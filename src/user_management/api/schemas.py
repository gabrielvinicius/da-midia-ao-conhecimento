# src/auth/api/schemas.py
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


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
