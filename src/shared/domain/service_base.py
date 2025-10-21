"""
Base service interfaces - consolidating common patterns
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from uuid import UUID

class IBaseValidator(ABC):
    """Base validation interface - eliminating validation duplication"""
    
    @abstractmethod
    def validate_input(self, data: Any) -> None:
        """Validate input data - raises exception if invalid."""
        pass

class IBaseMetrics(ABC):
    """Base metrics interface - eliminating metrics duplication"""
    
    @abstractmethod
    def record_operation_start(self, operation_id: UUID, operation_type: str) -> None:
        """Record operation start."""
        pass
    
    @abstractmethod
    def record_operation_success(self, operation_id: UUID, duration: float) -> None:
        """Record successful operation."""
        pass
    
    @abstractmethod
    def record_operation_failure(self, operation_id: UUID, error: str) -> None:
        """Record failed operation."""
        pass

class IBaseNotificationService(ABC):
    """Base notification interface - eliminating notification duplication"""
    
    @abstractmethod
    async def notify_started(self, user_id: str, operation_id: str, operation_type: str) -> None:
        """Notify operation started."""
        pass
    
    @abstractmethod
    async def notify_completed(self, user_id: str, operation_id: str, result: Any) -> None:
        """Notify operation completed."""
        pass
    
    @abstractmethod
    async def notify_failed(self, user_id: str, operation_id: str, error: str) -> None:
        """Notify operation failed."""
        pass

class IBaseStateManager(ABC):
    """Base state management interface - eliminating state duplication"""
    
    @abstractmethod
    async def update_status(self, entity_id: UUID, status: str, error: Optional[str] = None) -> None:
        """Update entity status."""
        pass
    
    @abstractmethod
    async def get_status(self, entity_id: UUID) -> Optional[str]:
        """Get entity status."""
        pass