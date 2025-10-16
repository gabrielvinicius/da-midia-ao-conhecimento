# src/topic_modeling/api/dependencies.py
from typing import Annotated, Any
from fastapi import Depends, Request

def get_container(request: Request) -> dict:
    return request.app.state.container

def get_topic_modeling_queries(container: Annotated[dict, Depends(get_container)]) -> Any:
    return container["topic_modeling_queries"]

def get_media_queries(container: Annotated[dict, Depends(get_container)]) -> Any:
    return container["media_queries"]
