from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")

class BaseResponseSchema(BaseModel, Generic[T]):
    status: str
    message: str
    data: Optional[T] = None
    error: Optional[Any] = None

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    limit: int
    pages: int

def create_success_response(data: Any, message: str = "Success") -> BaseResponseSchema:
    return BaseResponseSchema(status="success", message=message, data=data)

def create_error_response(error: Any, message: str = "Error") -> BaseResponseSchema:
    return BaseResponseSchema(status="error", message=message, error=error)
