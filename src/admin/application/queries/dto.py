from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID


class GetSystemStatsQuery(BaseModel):
    
    class Config:
        frozen = True


class GetSystemHealthQuery(BaseModel):
    
    class Config:
        frozen = True


class GetMediaProcessingStatsQuery(BaseModel):
    
    class Config:
        frozen = True


class GetUserActivityQuery(BaseModel):
    user_id: UUID = Field(..., description="ID of the user to retrieve activity stats for.")
    
    class Config:
        frozen = True
