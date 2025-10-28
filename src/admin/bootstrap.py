# src/admin/bootstrap.py
"""Helper utilities to bootstrap the admin module."""

from typing import Dict, Any

from src.admin.application.queries.admin_queries import AdminQueries
from src.auth.application.queries.auth_queries import AuthQueries
from src.media_management.application.queries.media_queries import MediaQueries


def bootstrap_admin_module(auth_queries: AuthQueries, media_queries: MediaQueries) -> Dict[str, Any]:
    """Return admin services wired with their dependencies."""

    admin_queries = AdminQueries(auth_queries=auth_queries, media_queries=media_queries)
    return {"admin_queries": admin_queries}