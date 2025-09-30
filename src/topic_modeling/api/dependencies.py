# src/topic_modeling/api/dependencies.py
from fastapi import Request, Depends
from typing import Annotated

from src.topic_modeling.application.queries.topic_modeling_queries import TopicModelingQueries
from src.media_management.application.queries.media_queries import MediaQueries

# --- Query Getter ---

def get_container(request: Request) -> dict:
    return request.app.state.container

def get_topic_modeling_queries(container: Annotated[dict, Depends(get_container)]) -> TopicModelingQueries:
    return container["topic_modeling_queries"]

# This will be needed for authorization
def get_media_queries(container: Annotated[dict, Depends(get_container)]) -> MediaQueries:
    return container["media_queries"]
