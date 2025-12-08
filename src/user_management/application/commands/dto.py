from pydantic import BaseModel, Field, EmailStr
from uuid import UUID
from typing import Optional

from src.user_management.domain.user import UserRole


class CreateUserCommand(BaseModel):
    email: EmailStr = Field(..., description="User's email address.")
    password: str = Field(..., description="User's password.")
    role: UserRole = Field(UserRole.USER, description="User's role.")


class UpdateUserCommand(BaseModel):
    user_id: UUID = Field(..., description="ID of the user to update.")
    email: Optional[str] = Field(None, description="New email address for the user.")
    password: Optional[str] = Field(None, description="New password for the user.")
    role: Optional[UserRole] = Field(None, description="New role for the user.")
    is_active: Optional[bool] = Field(None, description="New active status for the user.")

    class Config:
        frozen = True # Make it immutable, like dataclass(frozen=True)


class DeleteUserCommand(BaseModel):
    user_id: UUID = Field(..., description="ID of the user to delete.")

    class Config:
        frozen = True # Make it immutable