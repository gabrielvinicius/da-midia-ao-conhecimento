from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID


class GetUserQuery(BaseModel):
    user_id: UUID = Field(..., description="ID of the user to retrieve.")

    class Config:
        frozen = True # Make it immutable


class ListUsersQuery(BaseModel):
    page: int = Field(1, ge=1, description="Page number for pagination.")
    limit: int = Field(50, ge=1, le=100, description="Number of items per page.")
    search: Optional[str] = Field(None, description="Search term for filtering users by email.")

    class Config:
        frozen = True # Make it immutable