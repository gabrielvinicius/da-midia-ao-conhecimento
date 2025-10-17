"""
Admin query interfaces following CQRS pattern
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from uuid import UUID


class IQuery(ABC):
    """Base interface for all queries in admin module"""
    pass


class IQueryHandler(ABC):
    """Base interface for query handlers"""
    
    @abstractmethod
    async def handle(self, query: IQuery) -> Any:
        """Handle query execution"""
        pass


class IAdminQueries(ABC):
    """Interface for admin queries"""
    
    @abstractmethod
    async def get_user_statistics(self) -> Dict[str, Any]:
        """Get user statistics"""
        pass
    
    @abstractmethod
    async def get_media_statistics(self) -> Dict[str, Any]:
        """Get media statistics"""
        pass
    
    @abstractmethod
    async def get_system_health(self) -> Dict[str, Any]:
        """Get system health status"""
        pass
    
    @abstractmethod
    async def get_audit_logs(
        self, 
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        user_id: Optional[UUID] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get audit logs"""
        pass