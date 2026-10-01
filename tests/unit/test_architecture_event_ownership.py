"""Cada evento de integração é criado só pelo módulo que o publica."""
import ast
from pathlib import Path

from src.shared.domain import events as integration_events

SRC = Path(__file__).resolve().parents[2] / "src"


def _published_events():
    return {
        name: cls.published_by
        for name, cls in vars(integration_events).items()
        if isinstance(cls, type)
        and issubclass(cls, integration_events.DomainEvent)
        and cls is not integration_events.DomainEvent
    }


def _event_constructions(path: Path, names):
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call):
            name = getattr(node.func, "id", getattr(node.func, "attr", None))
            if name in names:
                yield name


def test_every_event_declares_who_publishes_it():
    owners = _published_events()
    assert owners  # os eventos existem
    modules = {p.name for p in SRC.iterdir() if p.is_dir()}
    assert set(owners.values()) <= modules


def test_events_are_only_created_by_their_publisher():
    owners = _published_events()
    violations = []
    for path in SRC.rglob("*.py"):
        module = path.relative_to(SRC).parts[0]
        for name in _event_constructions(path, owners):
            if owners[name] != module:
                violations.append(f"{path.relative_to(SRC)} cria {name} (publicado por {owners[name]})")
    assert violations == []
