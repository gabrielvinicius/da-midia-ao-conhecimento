"""
Unified API schemas - eliminating schema duplication
"""
from typing import Any, Dict, Optional, List, Generic, TypeVar
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

T = TypeVar('T')

class StatusEnum(str, Enum):
    """Common status values"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class EntityTypeEnum(str, Enum):
    """Entity types"""
    MEDIA = "media"
    TRANSCRIPTION = "transcription"
    SUMMARY = "summary"
    TOPIC_MODELING = "topic_modeling"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    USER = "user"

# Base schemas
class BaseResponseSchema(BaseModel, Generic[T]):
    """Base response schema for all APIs"""
    success: bool
    data: Optional[T] = None
    message: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class BaseEntitySchema(BaseModel):
    """Base schema for all entities"""
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    status: StatusEnum = StatusEnum.PENDING

class BasePaginationSchema(BaseModel):
    """Base pagination schema"""
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=10, ge=1, le=100)
    total: Optional[int] = None
    has_next: Optional[bool] = None

class BaseProcessingRequestSchema(BaseModel):
    """Base schema for processing requests"""
    entity_id: str
    user_id: str
    provider: Optional[str] = None
    options: Dict[str, Any] = Field(default_factory=dict)

class BaseProcessingResultSchema(BaseModel):
    """Base schema for processing results"""
    entity_id: str
    status: StatusEnum
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration: Optional[float] = None  # seconds

# Specific entity schemas
class MediaSchema(BaseEntitySchema):
    """Media entity schema"""
    filename: str
    file_size: int
    mime_type: str
    storage_path: str
    user_id: str

class TranscriptionSchema(BaseEntitySchema):
    """Transcription entity schema"""
    media_id: str
    text: Optional[str] = None
    language: Optional[str] = None
    provider: Optional[str] = None
    confidence: Optional[float] = None
    duration: Optional[float] = None

class SummarySchema(BaseEntitySchema):
    """Summary entity schema"""
    media_id: str
    text: Optional[str] = None
    provider: Optional[str] = None
    original_length: Optional[int] = None
    summary_length: Optional[int] = None

class TopicModelingSchema(BaseEntitySchema):
    """Topic modeling entity schema"""
    media_id: str
    topics: Optional[List[Dict[str, Any]]] = None
    provider: Optional[str] = None
    num_topics: Optional[int] = None
    coherence_score: Optional[float] = None

class UserSchema(BaseEntitySchema):
    """User entity schema"""
    email: str
    username: str
    is_active: bool = True
    role: str = "user"

# Request schemas
class ProcessingRequestSchema(BaseProcessingRequestSchema):
    """Generic processing request"""
    entity_type: EntityTypeEnum

class FileUploadRequestSchema(BaseModel):
    """File upload request"""
    filename: str
    user_id: str
    storage_provider: Optional[str] = "local"

# Response schemas
class SuccessResponseSchema(BaseResponseSchema[T]):
    """Success response schema"""
    success: bool = True

class ErrorResponseSchema(BaseResponseSchema[None]):
    """Error response schema"""
    success: bool = False
    data: None = None

class PaginatedResponseSchema(BaseResponseSchema[List[T]]):
    """Paginated response schema"""
    pagination: BasePaginationSchema

# Status schemas
class HealthCheckSchema(BaseModel):
    """Health check schema"""
    status: str = "healthy"
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    services: Dict[str, str] = Field(default_factory=dict)

class MetricsSchema(BaseModel):
    """Metrics schema"""
    name: str
    value: float
    labels: Dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Utility functions
def create_success_response(data: Any, message: str = "Success") -> SuccessResponseSchema:
    """Create success response"""
    return SuccessResponseSchema(data=data, message=message)

def create_error_response(error: str, message: str = "Error") -> ErrorResponseSchema:
    """Create error response"""
    return ErrorResponseSchema(error=error, message=message)

def create_paginated_response(
    data: List[Any], 
    page: int, 
    limit: int, 
    total: int
) -> PaginatedResponseSchema:
    """Create paginated response"""
    return PaginatedResponseSchema(
        data=data,
        pagination=BasePaginationSchema(
            page=page,
            limit=limit,
            total=total,
            has_next=page * limit < total
        )
    )