# src/topic_modeling/api/dependencies.py
from typing import Annotated, Any
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.topic_modeling.bootstrap import TopicModelingContainer
from src.topic_modeling.application.topic_modeling_service import TopicModelingService
from src.topic_modeling.application.commands.handlers import AnalyzeTopicsCommandHandler

def get_topic_modeling_container(
    request: Request
) -> TopicModelingContainer:
    """Get the topic modeling dependency injection container from request."""
    return request.app.state.container["topic_modeling_container"]

def get_topic_modeling_service(
    container: Annotated[TopicModelingContainer, Depends(get_topic_modeling_container)]
) -> TopicModelingService:
    """Get topic modeling service dependency."""
    return container.topic_modeling_service()

def get_analyze_topics_command_handler(
    container: Annotated[TopicModelingContainer, Depends(get_topic_modeling_container)]
) -> AnalyzeTopicsCommandHandler:
    """Get analyze topics command handler dependency."""
    return container.analyze_topics_command_handler()
