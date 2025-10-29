"""Minimal command pattern scaffolding used by legacy modules."""
from __future__ import annotations

from typing import Any, Callable, Dict, Type


class Command:
    """Base type for CQRS commands."""


class CommandHandler:
    """Base handler that processes commands."""

    async def handle(self, command: Command) -> Any:  # pragma: no cover - to be overridden
        raise NotImplementedError


class CommandBus:
    """Simple in-memory command bus."""

    def __init__(self) -> None:
        self._handlers: Dict[Type[Command], CommandHandler] = {}

    def register(self, command_type: Type[Command], handler: CommandHandler) -> None:
        self._handlers[command_type] = handler

    async def execute(self, command: Command) -> Any:
        handler = self._handlers.get(type(command))
        if handler is None:
            raise ValueError(f"No handler registered for command type {type(command)!r}")
        return await handler.handle(command)


__all__ = ["Command", "CommandHandler", "CommandBus"]
