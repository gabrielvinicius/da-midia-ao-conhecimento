from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

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
