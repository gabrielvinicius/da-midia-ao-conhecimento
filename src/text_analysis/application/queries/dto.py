from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID


class GetAnalysisQuery(BaseModel):
    analysis_id: UUID = Field(..., description="ID of the text analysis result.")
    
    class Config:
        frozen = True


class GetAnalysisByMediaIdQuery(BaseModel):
    media_id: UUID = Field(..., description="ID of the media associated with the analysis.")
    
    class Config:
        frozen = True


class ListTopicsQuery(BaseModel):
    analysis_id: UUID = Field(..., description="ID of the analysis to list topics for.")
    
    class Config:
        frozen = True