"""Cada serviço de aplicação é montado num único lugar.

Montagens repetidas divergiam: a API gravava sempre no armazenamento local,
a estimativa de tempo só existia na montagem que recebia o repositório de
durações, e a API da análise recebia uma consulta sem os métodos usados.
Agora a API, os workers e os handlers usam as mesmas fábricas
(infrastructure/dependencies/builders.py de cada módulo).
"""
import ast
from collections import defaultdict
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src"


def _application_classes():
    """Serviços e handlers definidos na camada de aplicação de cada módulo."""
    names = set()
    for path in SRC.glob("*/application/**/*.py"):
        if "services" not in path.parts and path.name != "event_handlers.py":
            continue
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            if isinstance(node, ast.ClassDef) and node.name.endswith(("Service", "Handlers", "Recovery", "Monitor")):
                names.add(node.name)
    return names


def _construction_sites(names):
    sites = defaultdict(set)
    for path in SRC.rglob("*.py"):
        if "application" in path.relative_to(SRC).parts:
            continue  # um serviço que compõe outro dentro da própria aplicação
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call):
                name = getattr(node.func, "id", getattr(node.func, "attr", None))
                if name in names:
                    sites[name].add(str(path.relative_to(SRC)))
    return sites


def test_each_application_service_is_built_in_a_single_place():
    sites = _construction_sites(_application_classes())
    assert "MediaService" in sites  # a verificação enxerga as montagens
    repeated = {name: sorted(files) for name, files in sites.items() if len(files) > 1}
    assert repeated == {}
