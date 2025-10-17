# src/admin/bootstrap.py
from sqlalchemy.ext.asyncio import AsyncSession
from src.admin.application.queries.admin_queries import AdminQueries
from src.media_management.application.queries.media_queries import MediaQueries

def bootstrap_admin_module(session: AsyncSession, media_queries: MediaQueries) -> dict:
    """Bootstrap the admin module with its dependencies."""
    
    # Create admin queries
    admin_queries = AdminQueries(session, media_queries)
    
    return {
        "admin_queries": admin_queries,
    }