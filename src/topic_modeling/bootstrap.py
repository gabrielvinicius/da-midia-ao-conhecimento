# src/topic_modeling/bootstrap.py
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from .application.queries.topic_modeling_queries import TopicModelingQueries
from .infrastructure.topic_modeling_repository import TopicModelingRepository
# The handler and its dependencies are constructed in the Celery task, not here.
# This bootstrap is for components needed by the synchronous API.

def bootstrap_topic_modeling_module(db_session: AsyncSession) -> Dict[str, Any]:
    """Constructs and returns the query services for the topic modeling module."""
    repository = TopicModelingRepository(db=db_session)
    queries = TopicModelingQueries(repository=repository)

    return {
        "topic_modeling_repository": repository,
        "topic_modeling_queries": queries,
    }
