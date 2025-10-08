# src/topic_modeling/api/dependencies.py
from fastapi import Request, Depends
from typing import Annotated

from src.topic_modeling.application.queries.topic_modeling_queries import TopicModelingQueries

# --- Query Getter ---

def get_container(request: Request) -> dict:
    return request.app.state.container

def get_topic_modeling_queries(container: Annotated[dict, Depends(get_container)]) -> TopicModelingQueries:
    return container["topic_modeling_queries"]

