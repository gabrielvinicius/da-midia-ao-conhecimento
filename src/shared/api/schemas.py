from typing import Generic, List, TypeVar

from pydantic import BaseModel, Field

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    """Generic schema for paginated API responses."""

    total_items: int = Field(..., description="The total number of items available.")
    total_pages: int = Field(..., description="The total number of pages.")
    current_page: int = Field(..., description="The current page number.")
    items: List[T] = Field(..., description="The list of items for the current page.")
