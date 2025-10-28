from typing import Annotated
from fastapi import Depends, Request

from src.topic_modeling.application.topic_modeling_service import TopicModelingService
from src.topic_modeling.infrastructure.topic_modeling_repository import TopicModelingRepository
from src.shared.application.modules import ModulesRegistry


def get_modules(request: Request) -> ModulesRegistry:
    return request.app.state.modules


def get_topic_modeling_service(
    modules: Annotated[ModulesRegistry, Depends(get_modules)]
) -> TopicModelingService:
    return modules.topic_modeling.service


def get_topic_modeling_repository(
    modules: Annotated[ModulesRegistry, Depends(get_modules)]
) -> TopicModelingRepository:
    return modules.topic_modeling.repository
