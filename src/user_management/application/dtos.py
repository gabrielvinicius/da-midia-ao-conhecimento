from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from src.user_management.domain import UserRole

# --- Commands ---

class CreateUserCommand(BaseModel):
    email: EmailStr = Field(..., description="User's email address.")
    password: str = Field(..., description="User's password.")
    role: UserRole = Field(UserRole.USER, description="User's role.")


class UpdateUserCommand(BaseModel):
    model_config = ConfigDict(frozen=True)
    user_id: UUID = Field(..., description="ID of the user to update.")
    email: Optional[str] = Field(None, description="New email address for the user.")
    password: Optional[str] = Field(None, description="New password for the user.")
    role: Optional[UserRole] = Field(None, description="New role for the user.")
    is_active: Optional[bool] = Field(
        None, description="New active status for the user."
    )


class DeleteUserCommand(BaseModel):
    model_config = ConfigDict(frozen=True)
    user_id: UUID = Field(..., description="ID of the user to delete.")
    admin_user_id: Optional[UUID] = Field(
        None, description="Admin performing the deletion."
    )

# --- Queries ---

class GetUserQuery(BaseModel):
    model_config = ConfigDict(frozen=True)
    user_id: UUID = Field(..., description="ID of the user to retrieve.")
    admin_user_id: Optional[UUID] = Field(
        None, description="Admin requesting the user."
    )


class ListUsersQuery(BaseModel):
    model_config = ConfigDict(frozen=True)
    page: int = Field(1, ge=1, description="Page number for pagination.")
    limit: int = Field(50, ge=1, le=100, description="Number of items per page.")
    search: Optional[str] = Field(
        None, description="Search term for filtering users by email."
    )
