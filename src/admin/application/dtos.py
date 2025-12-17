from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.user_management.domain import UserRole

# --- Commands ---

class DeleteMediaCommand(BaseModel):
    model_config = ConfigDict(frozen=True)
    media_id: UUID = Field(..., description="ID of the media to delete.")
    admin_user_id: Optional[UUID] = Field(
        None,
        description="ID of the admin user performing the action.",
    )
    reason: Optional[str] = Field(None, description="Reason for deletion.")


class DeleteUserCommand(BaseModel):
    model_config = ConfigDict(frozen=True)
    user_id: UUID = Field(..., description="ID of the user to delete.")
    admin_user_id: UUID = Field(
        ...,
        description="ID of the admin user performing the action.",
    )
    reason: Optional[str] = Field(None, description="Reason for deletion.")


class ReprocessMediaCommand(BaseModel):
    model_config = ConfigDict(frozen=True)
    media_id: UUID = Field(..., description="ID of the media to reprocess.")
    admin_user_id: UUID = Field(
        ...,
        description="ID of the admin user performing the action.",
    )
    force: bool = Field(
        False,
        description="Force reprocessing even if not in a failed state.",
    )


class UpdateUserRoleCommand(BaseModel):
    model_config = ConfigDict(frozen=True)
    user_id: UUID = Field(..., description="ID of the user to update role.")
    new_role: UserRole = Field(..., description="The new role for the user.")
    admin_user_id: UUID = Field(
        ...,
        description="ID of the admin user performing the action.",
    )
    reason: Optional[str] = Field(None, description="Reason for role update.")


class BulkReprocessFailedMediaCommand(BaseModel):
    model_config = ConfigDict(frozen=True)
    admin_user_id: UUID = Field(
        ...,
        description="ID of the admin user performing the action.",
    )

# --- Queries ---

class GetSystemStatsQuery(BaseModel):
    model_config = ConfigDict(frozen=True)


class GetSystemHealthQuery(BaseModel):
    model_config = ConfigDict(frozen=True)


class GetMediaProcessingStatsQuery(BaseModel):
    model_config = ConfigDict(frozen=True)


class GetUserActivityQuery(BaseModel):
    model_config = ConfigDict(frozen=True)
    user_id: UUID = Field(
        ...,
        description="ID of the user to retrieve activity stats for.",
    )
