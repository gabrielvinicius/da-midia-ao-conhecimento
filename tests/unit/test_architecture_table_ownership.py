"""Cada tabela é consultada só pelo módulo que a define.

O import-linter verifica imports, mas não enxerga uma consulta que cita a
tabela de outro módulo pelo nome (SQL em texto ou table("...")). Este teste
cobre esse caso. Chaves estrangeiras são permitidas: são integridade no
banco, declaradas no modelo, e não consultas.
"""
import ast
import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src"
MODULES = [p.name for p in SRC.iterdir() if p.is_dir() and (p / "__init__.py").exists()]


def _tables_by_module() -> dict:
    owners = {}
    for module in MODULES:
        for path in (SRC / module).rglob("*.py"):
            for match in re.finditer(r"__tablename__\s*=\s*[\"'](\w+)[\"']", path.read_text(encoding="utf-8")):
                owners[match.group(1)] = module
    return owners


def _table_references(path: Path):
    """Tabelas citadas em table("...") e em SQL escrito como texto."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = getattr(node.func, "id", getattr(node.func, "attr", ""))
            if name == "table" and node.args and isinstance(node.args[0], ast.Constant):
                yield str(node.args[0].value)
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            for match in re.finditer(r"\b(?:FROM|JOIN|UPDATE|INTO)\s+(\w+)", node.value, re.IGNORECASE):
                yield match.group(1)


def test_tables_are_only_queried_by_their_owner_module():
    owners = _tables_by_module()
    assert {"media", "transcriptions", "knowledge_chunks"} <= set(owners)
    violations = []
    for module in MODULES:
        for path in (SRC / module).rglob("*.py"):
            for table in _table_references(path):
                owner = owners.get(table)
                if owner and owner != module:
                    violations.append(f"{path.relative_to(SRC)} cita a tabela {table} ({owner})")
    assert violations == []


def test_the_check_catches_a_foreign_table(tmp_path):
    probe = tmp_path / "probe.py"
    probe.write_text('q = "SELECT id FROM media"\nt = table("transcriptions")\n', encoding="utf-8")
    assert list(_table_references(probe)) == ["media", "transcriptions"]
