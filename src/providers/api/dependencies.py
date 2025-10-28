"""Provider module API dependencies."""
from typing import Annotated, Any
from fastapi import Depends, Request

from src.shared.application.modules import ModulesRegistry


def get_modules(request: Request) -> ModulesRegistry:
    """Return the bootstrapped modules registry."""
    return request.app.state.modules


def get_provider_registry(modules: Annotated[ModulesRegistry, Depends(get_modules)]) -> Any:
    """Expose the provider registry."""
    return modules.providers.provider_registry
