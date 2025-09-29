# src/auth/api/schemas.py
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr = Field(..., description="The user's email address.", example="user@example.com")
    password: str = Field(..., description="The user's password (min 8 characters).", example="a_strong_password")


class TokenRequest(BaseModel):
    """Schema for requesting a token with username and password."""
    username: str = Field(..., description="The user's email address.", example="user@example.com")
    password: str = Field(..., description="The user's password.", example="a_strong_password")


class Token(BaseModel):
    """Schema for the response containing the access token."""
    access_token: str = Field(..., description="The JWT access token.", example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
    token_type: str = Field(..., description="The type of the token.", example="bearer")


class UserResponse(BaseModel):
    """Schema for returning user information safely."""
    id: UUID = Field(..., description="The unique identifier for the user.", example="f47ac10b-58cc-4372-a567-0e02b2c3d479")
    email: EmailStr = Field(..., description="The user's email address.", example="user@example.com")

    class Config:
        from_attributes = True
