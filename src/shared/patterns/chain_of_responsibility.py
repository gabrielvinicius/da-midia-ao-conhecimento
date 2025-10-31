"""Lightweight chain-of-responsibility utilities for placeholder pipelines."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol


class ProcessingContext:
    """Execution context shared across handlers."""

    def __init__(self, request: Any):
        self.request = request
        self.metadata: Dict[str, Any] = {}
        self.errors: List[str] = []

    def add_metadata(self, key: str, value: Any) -> None:
        self.metadata[key] = value

    def add_error(self, message: str) -> None:
        self.errors.append(message)

    def is_successful(self) -> bool:
        return not self.errors


@dataclass
class HandlerResult:
    succeeded: bool
    metadata: Dict[str, Any] | None = None
    error: Optional[str] = None


class BaseHandler:
    """Base asynchronous handler with chaining support."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._next: Optional[BaseHandler] = None

    def set_next(self, handler: "BaseHandler") -> "BaseHandler":
        self._next = handler
        return handler

    async def handle(self, context: ProcessingContext) -> None:
        await self._handle(context)
        if context.is_successful() and self._next is not None:
            await self._next.handle(context)

    async def _handle(self, context: ProcessingContext) -> None:  # pragma: no cover - to be overridden
        raise NotImplementedError


class ValidationHandler(BaseHandler):
    async def _handle(self, context: ProcessingContext) -> None:
        is_valid = await self.validate(context)
        if not is_valid:
            context.add_error(f"Validation '{self.name}' failed")

    async def validate(self, context: ProcessingContext) -> bool:  # pragma: no cover
        raise NotImplementedError


class TransformationHandler(BaseHandler):
    async def _handle(self, context: ProcessingContext) -> None:
        await self.transform(context)

    async def transform(self, context: ProcessingContext) -> None:  # pragma: no cover
        raise NotImplementedError


class FilterHandler(BaseHandler):
    async def _handle(self, context: ProcessingContext) -> None:
        should_continue = await self.filter(context)
        if not should_continue:
            context.add_error(f"Filter '{self.name}' stopped processing")

    async def filter(self, context: ProcessingContext) -> bool:  # pragma: no cover
        raise NotImplementedError


class ChainBuilder:
    """Helper that assembles handler chains."""

    def __init__(self, name: str):
        self.name = name
        self._handlers: List[BaseHandler] = []

    def add_validation(self, handler: ValidationHandler) -> "ChainBuilder":
        self._handlers.append(handler)
        return self

    def add_transformation(self, handler: TransformationHandler) -> "ChainBuilder":
        self._handlers.append(handler)
        return self

    def add_filter(self, handler: FilterHandler) -> "ChainBuilder":
        self._handlers.append(handler)
        return self

    def build(self) -> Optional[BaseHandler]:
        iterator = iter(self._handlers)
        first = next(iterator, None)
        current = first
        for handler in iterator:
            assert current is not None
            current = current.set_next(handler)
        return first


class ProcessingPipeline:
    """Executes a linked chain of handlers."""

    def __init__(self, name: str, first_handler: Optional[BaseHandler]):
        self.name = name
        self.first_handler = first_handler

    async def execute(self, request: Any) -> ProcessingContext:
        context = ProcessingContext(request)
        if self.first_handler is not None:
            await self.first_handler.handle(context)
        return context


class PipelineRegistry:
    """Global registry for sharing pipelines."""

    _pipelines: Dict[str, ProcessingPipeline] = {}

    @classmethod
    def register_pipeline(cls, name: str, pipeline: ProcessingPipeline) -> None:
        cls._pipelines[name] = pipeline

    @classmethod
    def get_pipeline(cls, name: str) -> Optional[ProcessingPipeline]:
        return cls._pipelines.get(name)


__all__ = [
    "ChainBuilder",
    "FilterHandler",
    "HandlerResult",
    "ProcessingContext",
    "ProcessingPipeline",
    "PipelineRegistry",
    "TransformationHandler",
    "ValidationHandler",
]
