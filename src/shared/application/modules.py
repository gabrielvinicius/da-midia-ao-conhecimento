"""Lightweight module registry and router helpers."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any, Iterable, Mapping, Sequence

from fastapi import FastAPI


def _import_string(path: str) -> Any:
    module_path, attribute = path.split(":", maxsplit=1)
    module = import_module(module_path)
    return getattr(module, attribute)


@dataclass(frozen=True)
class ModuleSpec:
    """Declarative description of an application module."""

    name: str
    binder_path: str
    routers: Sequence[str] = ()
    optional: bool = False


DEFAULT_MODULE_SPECS: tuple[ModuleSpec, ...] = (
    ModuleSpec(
        name="auth",
        binder_path="src.user_management.bootstrap:bind_user_management_module",
        routers=("src.user_management.api.routers:router",),
    ),
    ModuleSpec(
        name="monitoring",
        binder_path="src.monitoring.bootstrap:bind_monitoring_module",
        routers=("src.monitoring.api.routers:router",),
    ),
    ModuleSpec(
        name="media",
        binder_path="src.media_management.bootstrap:bind_media_module",
        routers=(
            "src.media_management.api.routes:router",
            "src.media_processing.api.routers:router",
        ),
    ),
    ModuleSpec(
        name="notifications",
        binder_path="src.notifications.bootstrap:bind_notification_module",
        routers=("src.notifications.api.routers:router",),
    ),
    ModuleSpec(
        name="providers",
        binder_path="src.providers.bootstrap:bind_providers_module",
        routers=("src.providers.api.routers:router",),
    ),
    ModuleSpec(
        name="text_analysis",
        binder_path="src.text_analysis.bootstrap:bind_text_analysis_module",
        routers=("src.text_analysis.api.routers:router",),
        optional=True,
    ),
    ModuleSpec(
        name="admin",
        binder_path="src.admin.bootstrap:bind_admin_module",
        routers=("src.admin.api.routers:router",),
    ),
)


def register_module_dependencies(
    app: FastAPI,
    module_instances: Mapping[str, Any],
    specs: Iterable[ModuleSpec] = DEFAULT_MODULE_SPECS,
) -> None:
    """Bind FastAPI dependency overrides for all declared modules."""

    for spec in specs:
        module = module_instances.get(spec.name)
        if module is None:
            if spec.optional:
                continue
            raise KeyError(f"Missing module instance for '{spec.name}'.")

        binder = _import_string(spec.binder_path)
        binder(app, module)


def include_module_routers(
    app: FastAPI,
    module_instances: Mapping[str, Any] | None = None,
    specs: Iterable[ModuleSpec] = DEFAULT_MODULE_SPECS,
) -> None:
    """Attach routers for modules that are enabled in this process."""

    for spec in specs:
        if module_instances is not None and module_instances.get(spec.name) is None:
            if spec.optional:
                continue
            raise KeyError(f"Missing module instance for '{spec.name}'.")

        for router_path in spec.routers:
            try:
                router = _import_string(router_path)
            except (ModuleNotFoundError, AttributeError):
                if spec.optional:
                    continue
                raise

            if router is not None:
                app.include_router(router)


__all__ = [
    "DEFAULT_MODULE_SPECS",
    "ModuleSpec",
    "include_module_routers",
    "register_module_dependencies",
]
