from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID

from src.user_management.domain.user import UserRole


class DeleteMediaCommand(BaseModel):
    media_id: UUID = Field(..., description="ID of the media to delete.")
    admin_user_id: Optional[UUID] = Field(None, description="ID of the admin user performing the action.")
    reason: Optional[str] = Field(None, description="Reason for deletion.")

    class Config:
        frozen = True


class DeleteUserCommand(BaseModel):
    user_id: UUID = Field(..., description="ID of the user to delete.")
    admin_user_id: UUID = Field(..., description="ID of the admin user performing the action.")
    reason: Optional[str] = Field(None, description="Reason for deletion.")

    class Config:
        frozen = True


class ReprocessMediaCommand(BaseModel):
    media_id: UUID = Field(..., description="ID of the media to reprocess.")
    admin_user_id: UUID = Field(..., description="ID of the admin user performing the action.")
    force: bool = Field(False, description="Force reprocessing even if not in a failed state.")

    class Config:
        frozen = True


class UpdateUserRoleCommand(BaseModel):
    user_id: UUID = Field(..., description="ID of the user to update role.")
    new_role: UserRole = Field(..., description="The new role for the user.")
    admin_user_id: UUID = Field(..., description="ID of the admin user performing the action.")
    reason: Optional[str] = Field(None, description="Reason for role update.")

    class Config:
        frozen = True


class BulkReprocessFailedMediaCommand(BaseModel):
    admin_user_id: UUID = Field(..., description="ID of the admin user performing the action.")
    
    class Config:
        frozen = True